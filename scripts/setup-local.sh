#!/usr/bin/env bash
# 一次性安装本地开发环境。幂等：已完成的步骤会跳过。
#
# 安装内容：
#   1. conda sc-wiki-infra 环境（mysqld / redis-server / openjdk21 / mysql-client）
#   2. Neo4j 5.26.29（从 neo4j:5 镜像提取，官方源被 CDN 地域封锁）
#   3. Qdrant 静态二进制（GitHub release 经 gh-proxy.com）
#   4. Go 工具链 → ~/.local/go
#   5. sc-wiki 环境的 Python 依赖
#   6. .data / .local 目录骨架、MySQL 配置与 datadir

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

# ── 1. conda infra 环境 ─────────────────────────────────────
setup_infra_env() {
  if [[ -x "$INFRA_BIN/mysqld" && -x "$INFRA_BIN/redis-server" && -x "$INFRA_BIN/java" ]]; then
    ok "conda 环境 sc-wiki-infra 已就绪"
    return
  fi
  info "创建 conda 环境 sc-wiki-infra（mysql-server 8.4 / redis-server / openjdk 21）"
  # 独立于 sc-wiki：混装会迫使 conda 将 python 从 pkgs/main 换成 conda-forge 版本，
  # 危及 sc-wiki 中已有的 161 个科学计算包。
  conda create -n sc-wiki-infra -c conda-forge --override-channels -y \
    'mysql-server=8.4' 'mysql-client=8.4' 'redis-server' 'openjdk=21' \
    || die "conda 环境创建失败"
  ok "sc-wiki-infra 创建完成"
}

# ── 2. Neo4j ────────────────────────────────────────────────
setup_neo4j() {
  if [[ -x "$NEO4J_HOME/bin/neo4j" ]]; then
    ok "Neo4j 已安装（$(rg -o 'Version: [0-9.]+' "$NEO4J_HOME/packaging_info" 2>/dev/null || echo 未知)）"
    return
  fi
  info "提取 Neo4j 5.26.29"
  # dist.neo4j.org / debian.neo4j.com / aliyun / tuna / ustc / 腾讯 / 华为镜像
  # 全部返回 403（CDN 地域封锁，带完整浏览器头亦然）。
  # neo4j:5 镜像内是纯 Java 应用，提取即可独立运行；提取后镜像可删除。
  docker image inspect neo4j:5 >/dev/null 2>&1 \
    || die "需要 neo4j:5 镜像来提取 Neo4j。先执行 docker pull neo4j:5"
  local tmp; tmp=$(mktemp -d)
  docker run --rm --entrypoint tar neo4j:5 cf - -C /var/lib neo4j 2>/dev/null \
    | tar xf - -C "$tmp" || die "Neo4j 提取失败"
  rm -rf "$NEO4J_HOME"
  mv "$tmp/neo4j" "$NEO4J_HOME"
  rmdir "$tmp"

  # 镜像内 data/logs 是指向 /data、/logs 的符号链接（Docker 特化）。
  # 不替换为真实目录，log4j 初始化会失败并导致启动中止。
  rm -f "$NEO4J_HOME/data" "$NEO4J_HOME/logs"
  ln -sfn "$DATA_DIR/neo4j/data" "$NEO4J_HOME/data"
  ln -sfn "$DATA_DIR/neo4j/logs" "$NEO4J_HOME/logs"

  # 监听地址与端口写入配置；认证沿用 .env 中的 NEO4J_PASSWORD。
  {
    echo ""
    echo "# ── 本地开发覆盖（scripts/setup-local.sh 追加）──"
    echo "server.bolt.listen_address=127.0.0.1:$NEO4J_BOLT_PORT"
    echo "server.http.listen_address=127.0.0.1:$NEO4J_HTTP_PORT"
    # 独立 run 目录：Neo4j 自己也写 neo4j.pid，与 dev.sh 的包装进程 pid 文件同名，
    # 放在一起会让 Neo4j 读到包装进程的 pid 而误判"已在运行"并拒绝启动。
    echo "server.directories.run=$LOCAL_DIR/run-neo4j"
  } >> "$NEO4J_HOME/conf/neo4j.conf"
  ok "Neo4j 已装到 .local/neo4j"
}

# ── 3. Qdrant ───────────────────────────────────────────────
setup_qdrant() {
  if [[ -x "$QDRANT_BIN" ]]; then
    ok "Qdrant 已安装（$("$QDRANT_BIN" --version 2>/dev/null | head -1)）"
    return
  fi
  info "下载 Qdrant $QDRANT_VERSION 静态二进制"
  # musl 静态版无动态库依赖，比 gnu 版更适合放在 conda 环境之外独立运行。
  local url="https://gh-proxy.com/https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-musl.tar.gz"
  local tmp; tmp=$(mktemp -d)
  curl -fsSL --max-time 600 -o "$tmp/q.tar.gz" "$url" || die "Qdrant 下载失败: $url"
  tar xzf "$tmp/q.tar.gz" -C "$tmp" || die "Qdrant 解包失败"
  install -m 755 "$tmp/qdrant" "$QDRANT_BIN"
  rm -rf "$tmp"

  # Qdrant 启动时读取 ./config/config.yaml（相对工作目录）。从镜像取一份，
  # 避免依赖 GitHub 上分散的配置文件。
  if [[ ! -f "$LOCAL_DIR/qdrant-config/config.yaml" ]]; then
    mkdir -p "$LOCAL_DIR/qdrant-config"
    docker run --rm --entrypoint tar qdrant/qdrant:latest cf - -C /qdrant config 2>/dev/null \
      | tar xf - -C "$LOCAL_DIR" --strip-components=0 2>/dev/null || true
    [[ -d "$LOCAL_DIR/config" ]] && mv "$LOCAL_DIR/config"/* "$LOCAL_DIR/qdrant-config/" \
      && rmdir "$LOCAL_DIR/config"
  fi
  ok "Qdrant 已装到 .local/bin/qdrant"
}

# ── 4. Go ───────────────────────────────────────────────────
setup_go() {
  if [[ -x "$GO_BIN" ]]; then
    ok "Go 已安装（$("$GO_BIN" version 2>/dev/null)）"
    return
  fi
  info "下载 Go $GO_VERSION → $GO_ROOT"
  local tmp; tmp=$(mktemp -d)
  curl -fsSL --max-time 900 -o "$tmp/go.tar.gz" \
    "https://mirrors.aliyun.com/golang/go${GO_VERSION}.linux-amd64.tar.gz" \
    || die "Go 下载失败"
  mkdir -p "$(dirname "$GO_ROOT")"
  rm -rf "$GO_ROOT"
  tar xzf "$tmp/go.tar.gz" -C "$(dirname "$GO_ROOT")" || die "Go 解包失败"
  rm -rf "$tmp"
  ok "Go 已装到 $GO_ROOT"
}

# ── 5. Python 依赖 ──────────────────────────────────────────
setup_python() {
  [[ -x "$PY_BIN/python" ]] || die "conda 环境 sc-wiki 不存在，请先 conda create -n sc-wiki python=3.12"
  info "安装 Python 依赖到 sc-wiki 环境"
  # watchfiles 供 uvicorn --reload 与 goserver 热重载使用（uvicorn 非 [standard] 不自带）。
  "$PY_BIN/python" -m pip install -q \
    -r "$REPO_ROOT/docker/requirements.txt" \
    -r "$REPO_ROOT/requirements-news.txt" \
    watchfiles || die "Python 依赖安装失败"
  ok "Python 依赖就绪"
}

# ── 6. 目录骨架与 MySQL ─────────────────────────────────────
setup_dirs() {
  info "创建数据目录骨架"
  mkdir -p "$DATA_DIR"/{mysql,redis,neo4j/data,neo4j/logs,qdrant/storage,qdrant/snapshots} \
           "$DATA_DIR"/{uploads,upload_PDFs,parsed_markdown,review_artifacts,clean_results,avatars} \
           "$RUN_DIR" "$LOG_DIR" "$LOCAL_DIR/bin"
  [[ -f "$DATA_DIR/prop_name_ai_cache.json" ]] || echo '{}' > "$DATA_DIR/prop_name_ai_cache.json"
  ok "目录骨架就绪"
}

setup_mysql_cnf() {
  # 系统 /etc/mysql/my.cnf 含 user=mysql 与 log_error=/var/log/mysql/error.log，
  # 以普通用户启动会失败。所有 mysql* 命令必须 --defaults-file 完全隔离。
  info "写入 MySQL 配置"
  cat > "$MYSQL_CNF" <<EOF
# SC-Wiki 本地 MySQL 配置（由 scripts/setup-local.sh 生成）
# 与系统 MySQL 完全隔离：独立 datadir、端口 $MYSQL_PORT、独立 socket。
[mysqld]
basedir                 = $INFRA_ENV
datadir                 = $DATA_DIR/mysql
socket                  = $MYSQL_SOCK
port                    = $MYSQL_PORT
bind-address            = 127.0.0.1
mysqlx                  = OFF
pid-file                = $RUN_DIR/mysql.pid
log-error               = $LOG_DIR/mysql.err
character-set-server    = utf8mb4
collation-server        = utf8mb4_unicode_ci
# 单用户开发环境，无需 binlog，省磁盘与写放大。
disable-log-bin
innodb_buffer_pool_size = 512M

[client]
socket                  = $MYSQL_SOCK
port                    = $MYSQL_PORT
host                    = 127.0.0.1
EOF
  chmod 600 "$MYSQL_CNF"
  ok "MySQL 配置写入 .local/my.cnf"
}

init_mysql_datadir() {
  if [[ -d "$DATA_DIR/mysql/mysql" ]]; then
    ok "MySQL datadir 已初始化"
    return
  fi
  info "初始化 MySQL datadir"
  "$INFRA_BIN/mysqld" --defaults-file="$MYSQL_CNF" --initialize-insecure \
    >>"$LOG_DIR/mysql-init.log" 2>&1 || die "MySQL 初始化失败，见 $LOG_DIR/mysql-init.log"
  ok "MySQL datadir 初始化完成（root 无密码，下一步创建业务账号）"
}

main() {
  info "SC-Wiki 本地开发环境安装"
  [[ -f "$REPO_ROOT/.env" ]] || die "缺少 .env，请先执行 python3 scripts/gen-env.py <旧.env> .env"
  setup_dirs
  setup_infra_env
  setup_mysql_cnf
  init_mysql_datadir
  setup_neo4j
  setup_qdrant
  setup_go
  setup_python
  echo
  ok "安装完成。下一步："
  echo "     scripts/migrate-from-docker.sh   # 迁移 Docker 数据"
  echo "     scripts/dev.sh start             # 启动全部服务"
}

main "$@"
