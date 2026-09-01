#!/usr/bin/env bash
# 一次性把 Docker 命名卷中的数据迁移到 .data/。
#
# 原卷全程只读，不删除、不修改。迁移失败可重跑；新栈验证通过后再由用户决定清理。
#
# 各服务迁移方式取决于版本差异：
#   MySQL   8.4.11 → 8.4.2  降级，必须 mysqldump 逻辑导出（拒绝打开高版本 datadir）
#   Neo4j   5.26.29 → 相同   物理拷贝
#   Qdrant  1.19.0  → 相同   物理拷贝
#   Redis   7.4.10 → 8.10.1 只拷 RDB（AOF 增量文件已损坏，且 RDB 才是向前兼容的格式）

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

load_env

COMPOSE_DIR=/home/mayuan/work/SC-Wiki-docker
COMPOSE_FILE=dev.yaml
PROJECT=sc-wiki-dev

# 卷内文件属主为 999:999(mysql) / 7474:7474(neo4j) 等，宿主机 chown 需 root，
# 故在一次性 alpine 容器内完成拷贝与属主修正。
copy_volume() {
  local vol=$1 dest=$2
  docker volume inspect "$vol" >/dev/null 2>&1 || { warn "卷 $vol 不存在，跳过"; return 1; }
  mkdir -p "$dest"
  docker run --rm \
    -v "$vol":/from:ro \
    -v "$dest":/to \
    alpine:latest sh -c \
    'cp -a /from/. /to/ 2>/dev/null; chown -R 1000:1000 /to' \
    || { warn "卷 $vol 拷贝失败"; return 1; }
  return 0
}

# ── MySQL：逻辑导出 ─────────────────────────────────────────
migrate_mysql() {
  info "迁移 MySQL（逻辑导出，8.4.11 → 8.4.2 降级）"
  local dump="$LOCAL_DIR/mysql-migration.sql"

  docker ps --format '{{.Names}}' | grep -q "^$PROJECT-mysql-1$" \
    || die "需要 $PROJECT-mysql-1 处于运行状态才能导出。先执行:
       docker compose -f $COMPOSE_DIR/$COMPOSE_FILE up -d mysql"

  # --single-transaction 保证一致性快照；不加 --databases 以便导入到同名库时更灵活。
  docker exec "$PROJECT-mysql-1" sh -c \
    'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers \
     --default-character-set=utf8mb4 --databases '"$MYSQL_DATABASE" \
    > "$dump" 2>"$LOG_DIR/mysqldump.err" \
    || die "导出失败，见 $LOG_DIR/mysqldump.err"

  local tables; tables=$(grep -c 'CREATE TABLE' "$dump" || true)
  (( tables > 0 )) || die "导出内容为空（0 张表），中止"
  ok "已导出 $tables 张表（$(du -h "$dump" | cut -f1)）"

  mysql_admin ping >/dev/null 2>&1 || die "本地 MySQL 未运行。先执行 scripts/dev.sh start mysql"

  info "导入本地 MySQL 并创建业务账号"
  mysql_cli -uroot < "$dump" || die "导入失败"

  # 业务账号：backend 与 goserver 都用 MYSQL_USER 连接，非 root。
  mysql_cli -uroot <<SQL || die "账号创建失败"
CREATE USER IF NOT EXISTS '$MYSQL_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';
CREATE USER IF NOT EXISTS '$MYSQL_USER'@'127.0.0.1' IDENTIFIED BY '$MYSQL_PASSWORD';
ALTER USER '$MYSQL_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';
ALTER USER '$MYSQL_USER'@'127.0.0.1' IDENTIFIED BY '$MYSQL_PASSWORD';
GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'localhost';
GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

  local n; n=$(mysql_cli -uroot -N -e \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$MYSQL_DATABASE';")
  ok "本地 MySQL 现有 $n 张表"
}

# ── Neo4j / Qdrant / Redis / 应用数据 ───────────────────────
migrate_neo4j() {
  info "迁移 Neo4j 数据（物理拷贝，版本相同 5.26.29）"
  [[ -z "$(ls -A "$DATA_DIR/neo4j/data" 2>/dev/null)" ]] \
    || { warn "$DATA_DIR/neo4j/data 非空，跳过（如需重来请先清空）"; return; }
  copy_volume "${PROJECT}_neo4j_data_dev" "$DATA_DIR/neo4j/data" \
    && ok "Neo4j 数据已迁移（$(du -sh "$DATA_DIR/neo4j/data" | cut -f1)）"
}

migrate_qdrant() {
  info "迁移 Qdrant 数据（物理拷贝，版本相同 1.19.0）"
  [[ -z "$(ls -A "$DATA_DIR/qdrant/storage" 2>/dev/null)" ]] \
    || { warn "$DATA_DIR/qdrant/storage 非空，跳过"; return; }
  copy_volume "${PROJECT}_qdrant_storage_dev" "$DATA_DIR/qdrant/storage" \
    && ok "Qdrant 数据已迁移（$(du -sh "$DATA_DIR/qdrant/storage" | cut -f1)）"
}

migrate_redis() {
  info "迁移 Redis 数据（仅 RDB）"
  # Docker 卷中的 appendonly.aof.3.incr.aof 已损坏（daemon 异常重启所致），
  # 只取 RDB 基线；Redis 存的是队列与缓存，非权威数据。
  local tmp; tmp=$(mktemp -d)
  if copy_volume "${PROJECT}_redis_data_dev" "$tmp"; then
    local rdb
    rdb=$(find "$tmp" -name '*.base.rdb' -o -name 'dump.rdb' 2>/dev/null | head -1)
    if [[ -n "$rdb" ]]; then
      cp "$rdb" "$DATA_DIR/redis/dump.rdb"
      ok "Redis RDB 已迁移（$(du -h "$DATA_DIR/redis/dump.rdb" | cut -f1)）"
    else
      warn "未找到 RDB 文件，Redis 将以空库启动（仅影响队列与缓存）"
    fi
  fi
  rm -rf "$tmp"
}

migrate_app_data() {
  info "迁移应用数据（上传文件、解析产物）"
  local pairs=(
    "${PROJECT}_upload_pdfs_dev:$DATA_DIR/upload_PDFs"
    "${PROJECT}_parsed_markdown_dev:$DATA_DIR/parsed_markdown"
    "${PROJECT}_review_artifacts_dev:$DATA_DIR/review_artifacts"
    "${PROJECT}_clean_results_dev:$DATA_DIR/clean_results"
    "${PROJECT}_uploads_dev:$DATA_DIR/uploads"
  )
  for p in "${pairs[@]}"; do
    copy_volume "${p%%:*}" "${p##*:}" && ok "${p%%:*} → ${p##*:}"
  done

  # 头像目录此前由 goserver 写在容器内（未挂卷），从运行中的容器拷出。
  if docker ps -a --format '{{.Names}}' | grep -q "^$PROJECT-goserver-1$"; then
    docker cp "$PROJECT-goserver-1:/data/avatars/." "$DATA_DIR/avatars/" 2>/dev/null \
      && ok "头像已迁移" || warn "头像迁移跳过（容器内无该目录）"
  fi

  # prop_name_ai_cache.json 原为 bind mount，直接从宿主机复制。
  local cache="$COMPOSE_DIR/data-local/prop_name_ai_cache.json"
  [[ -f "$cache" ]] && cp "$cache" "$DATA_DIR/prop_name_ai_cache.json" \
    && ok "prop_name_ai_cache.json 已迁移"
}

main() {
  info "从 Docker 迁移数据到 .data/（原卷保持只读，不删除）"
  echo
  migrate_mysql
  migrate_neo4j
  migrate_qdrant
  migrate_redis
  migrate_app_data
  echo
  ok "迁移完成。下一步：scripts/dev.sh start"
}

main "$@"
