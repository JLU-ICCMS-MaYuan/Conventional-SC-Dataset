#!/usr/bin/env bash
# 本地开发环境启停编排。
#
#   scripts/dev.sh start [服务...]   启动（缺省全部）
#   scripts/dev.sh stop  [服务...]   停止
#   scripts/dev.sh status            查看状态
#   scripts/dev.sh logs <服务>       跟踪日志
#
# 服务名：mysql redis neo4j qdrant python worker goserver frontend
# news-worker / news-scheduler 需显式指定，日常开发用不上。

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

INFRA_SERVICES=(mysql redis neo4j qdrant)
APP_SERVICES=(python worker goserver frontend)
ALL_SERVICES=("${INFRA_SERVICES[@]}" "${APP_SERVICES[@]}")

# ── 通用进程管理 ────────────────────────────────────────────

# spawn <名称> <命令...>  以 setsid 启动后台进程并记录 pid
spawn() {
  local name=$1; shift
  setsid "$@" >>"$LOG_DIR/$name.log" 2>&1 &
  echo $! > "$RUN_DIR/$name.pid"
}

# 优雅停止：先 TERM，超时再 KILL
stop_pid() {
  # 必须分两行：bash 在执行 local 前会先展开整行所有词，
  # 写成 `local name=$1 f="...$name..."` 时 $name 尚未赋值，set -u 下直接报错。
  local name=$1
  local f="$RUN_DIR/$name.pid"
  [[ -f "$f" ]] || return 0
  local p; p=$(cat "$f" 2>/dev/null || true)
  if [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; then
    kill -TERM "-$p" 2>/dev/null || kill -TERM "$p" 2>/dev/null || true
    local i=0
    # ++i 而非 i++：后缀形式在 i=0 时返回 1，set -e 下会中断整个停止流程。
    while (( i < 15 )) && kill -0 "$p" 2>/dev/null; do sleep 1; ((++i)); done
    kill -0 "$p" 2>/dev/null && { kill -9 "-$p" 2>/dev/null || kill -9 "$p" 2>/dev/null || true; }
  fi
  rm -f "$f"
}

# ── 各服务启动 ──────────────────────────────────────────────

start_mysql() {
  mysql_admin ping >/dev/null 2>&1 && { ok "mysql 已在运行"; return; }
  port_busy "$MYSQL_PORT" && die "端口 $MYSQL_PORT 已被占用"
  spawn mysql "$INFRA_BIN/mysqld" --defaults-file="$MYSQL_CNF"
  wait_for 60 "mysql" mysql_admin ping || die "mysql 启动失败，见 $LOG_DIR/mysql.err"
  ok "mysql  127.0.0.1:$MYSQL_PORT"
}

# </dev/null：redis-cli 在非交互场景下会等待 stdin 而挂住。
redis_ready() { "$INFRA_BIN/redis-cli" -p "$REDIS_PORT" ping </dev/null 2>/dev/null | grep -q PONG; }

start_redis() {
  redis_ready && { ok "redis 已在运行"; return; }
  port_busy "$REDIS_PORT" && die "端口 $REDIS_PORT 已被占用"
  # appendonly no：AOF 增量文件易在异常退出后损坏（Docker 栈已踩过），
  # 开发环境 Redis 只存队列与缓存，RDB 快照足够。
  spawn redis "$INFRA_BIN/redis-server" \
    --dir "$DATA_DIR/redis" --port "$REDIS_PORT" --bind 127.0.0.1 \
    --appendonly no --save '300 10' --daemonize no
  wait_for 30 "redis" redis_ready || die "redis 启动失败"
  ok "redis  127.0.0.1:$REDIS_PORT"
}

neo4j_ready() { curl -sf --max-time 3 "http://127.0.0.1:$NEO4J_HTTP_PORT/" >/dev/null 2>&1; }

start_neo4j() {
  neo4j_ready && { ok "neo4j 已在运行"; return; }
  port_busy "$NEO4J_BOLT_PORT" && die "端口 $NEO4J_BOLT_PORT 已被占用"
  # 首次启动前设置初始密码，使 .env 中的 NEO4J_PASSWORD 生效。
  if [[ ! -d "$DATA_DIR/neo4j/data/dbms" ]]; then
    info "设置 Neo4j 初始密码"
    JAVA_HOME="$INFRA_ENV" NEO4J_HOME="$NEO4J_HOME" \
      "$NEO4J_HOME/bin/neo4j-admin" dbms set-initial-password "$NEO4J_PASSWORD" \
      >>"$LOG_DIR/neo4j.log" 2>&1 || warn "初始密码设置失败（可能已设置过）"
  fi
  spawn neo4j env JAVA_HOME="$INFRA_ENV" NEO4J_HOME="$NEO4J_HOME" "$NEO4J_HOME/bin/neo4j" console
  wait_for 120 "neo4j" neo4j_ready || die "neo4j 启动失败，见 $LOG_DIR/neo4j.log"
  ok "neo4j  bolt://127.0.0.1:$NEO4J_BOLT_PORT"
}

qdrant_ready() { curl -sf --max-time 3 "http://127.0.0.1:$QDRANT_PORT/readyz" >/dev/null 2>&1; }

start_qdrant() {
  qdrant_ready && { ok "qdrant 已在运行"; return; }
  port_busy "$QDRANT_PORT" && die "端口 $QDRANT_PORT 已被占用"
  # storage 与 snapshots 都必须显式指定：缺 snapshots 时 qdrant 会 panic 退出（exit 101）。
  # 工作目录设为 .local，使其能找到 qdrant-config/ 下的默认配置。
  ( cd "$LOCAL_DIR" && spawn qdrant env \
      QDRANT__STORAGE__STORAGE_PATH="$DATA_DIR/qdrant/storage" \
      QDRANT__STORAGE__SNAPSHOTS_PATH="$DATA_DIR/qdrant/snapshots" \
      QDRANT__SERVICE__HTTP_PORT="$QDRANT_PORT" \
      QDRANT__SERVICE__GRPC_PORT="$QDRANT_GRPC_PORT" \
      QDRANT__SERVICE__HOST=127.0.0.1 \
      "$QDRANT_BIN" )
  wait_for 60 "qdrant" qdrant_ready || die "qdrant 启动失败，见 $LOG_DIR/qdrant.log"
  ok "qdrant 127.0.0.1:$QDRANT_PORT"
}

py_ready() { curl -sf --max-time 3 "http://127.0.0.1:$PYTHON_PORT/health" >/dev/null 2>&1; }

start_python() {
  py_ready && { ok "python 已在运行"; return; }
  port_busy "$PYTHON_PORT" && die "端口 $PYTHON_PORT 已被占用"
  info "运行数据库迁移"
  ( cd "$REPO_ROOT" && "$PY_BIN/python" -m backend.scripts.run_migrations ) \
    >>"$LOG_DIR/migrate.log" 2>&1 || die "迁移失败，见 $LOG_DIR/migrate.log"
  ok "迁移完成"
  # --reload 依赖 watchfiles；只监听 backend/ 避免 .data 写入触发重启。
  ( cd "$REPO_ROOT" && spawn python "$PY_BIN/uvicorn" backend.main:app \
      --host 127.0.0.1 --port "$PYTHON_PORT" --reload --reload-dir backend )
  wait_for 90 "python" py_ready || die "python 启动失败，见 $LOG_DIR/python.log"
  ok "python 127.0.0.1:$PYTHON_PORT (--reload)"
}

start_worker() {
  pid_alive worker && { ok "worker 已在运行"; return; }
  ( cd "$REPO_ROOT" && spawn worker "$PY_BIN/rq" worker \
      --url "$REDIS_URL" --with-scheduler scwiki-upload )
  sleep 2
  pid_alive worker || die "worker 启动失败，见 $LOG_DIR/worker.log"
  ok "worker (rq scwiki-upload)"
}

start_goserver() {
  pid_alive goserver && { ok "goserver 已在运行"; return; }
  port_busy "$GOSERVER_PORT" && die "端口 $GOSERVER_PORT 已被占用"
  spawn goserver "$REPO_ROOT/scripts/goserver-watch.sh"
  wait_for 120 "goserver" curl -sf --max-time 3 "http://127.0.0.1:$GOSERVER_PORT/health" \
    || die "goserver 启动失败，见 $LOG_DIR/goserver.log"
  ok "goserver 127.0.0.1:$GOSERVER_PORT (热重载)"
}

start_frontend() {
  pid_alive frontend && { ok "frontend 已在运行"; return; }
  port_busy "$VITE_PORT" && die "端口 $VITE_PORT 已被占用"
  [[ -d "$REPO_ROOT/frontend/node_modules" ]] || die "缺少 frontend/node_modules，先执行 npm ci"
  ( cd "$REPO_ROOT/frontend" && spawn frontend npm run dev )
  wait_for 60 "frontend" curl -sf --max-time 3 "http://127.0.0.1:$VITE_PORT/" \
    || die "frontend 启动失败，见 $LOG_DIR/frontend.log"
  ok "frontend http://127.0.0.1:$VITE_PORT  ← 浏览器入口"
}

start_news_worker()    { pid_alive news-worker && return
  ( cd "$REPO_ROOT" && spawn news-worker "$PY_BIN/python" -m backend.news worker ); ok "news-worker"; }
start_news_scheduler() { pid_alive news-scheduler && return
  ( cd "$REPO_ROOT" && spawn news-scheduler "$PY_BIN/python" -m backend.news schedule ); ok "news-scheduler"; }

# ── 停止 ────────────────────────────────────────────────────

stop_mysql() {
  if mysql_admin ping >/dev/null 2>&1; then
    mysql_admin shutdown >/dev/null 2>&1 || true
    local i=0; while (( i<20 )) && mysql_admin ping >/dev/null 2>&1; do sleep 1; ((++i)); done
  fi
  stop_pid mysql; ok "mysql 已停止"
}

stop_redis() {
  "$INFRA_BIN/redis-cli" -p "$REDIS_PORT" shutdown nosave </dev/null >/dev/null 2>&1 || true
  stop_pid redis; ok "redis 已停止"
}

stop_neo4j() {
  if [[ -x "$NEO4J_HOME/bin/neo4j" ]]; then
    JAVA_HOME="$INFRA_ENV" NEO4J_HOME="$NEO4J_HOME" "$NEO4J_HOME/bin/neo4j" stop \
      >>"$LOG_DIR/neo4j.log" 2>&1 || true
  fi
  stop_pid "neo4j"; ok "neo4j 已停止"
}

stop_generic() { stop_pid "$1"; ok "$1 已停止"; }

# ── status / logs ───────────────────────────────────────────

status() {
  printf '%-16s %-10s %s\n' 服务 状态 地址
  printf '%-16s %-10s %s\n' ---- ---- ----
  local checks=(
    "mysql|mysql_admin ping|127.0.0.1:$MYSQL_PORT"
    "redis|redis_ready|127.0.0.1:$REDIS_PORT"
    "neo4j|neo4j_ready|bolt://127.0.0.1:$NEO4J_BOLT_PORT"
    "qdrant|qdrant_ready|127.0.0.1:$QDRANT_PORT"
    "python|py_ready|127.0.0.1:$PYTHON_PORT"
    "goserver|curl -sf --max-time 3 http://127.0.0.1:$GOSERVER_PORT/health|127.0.0.1:$GOSERVER_PORT"
    "frontend|curl -sf --max-time 3 http://127.0.0.1:$VITE_PORT/|http://127.0.0.1:$VITE_PORT"
  )
  for entry in "${checks[@]}"; do
    IFS='|' read -r name cmd addr <<< "$entry"
    if eval "$cmd" >/dev/null 2>&1; then
      printf '%-16s \033[0;32m%-10s\033[0m %s\n' "$name" 运行中 "$addr"
    else
      printf '%-16s \033[0;31m%-10s\033[0m %s\n' "$name" 已停止 "$addr"
    fi
  done
  for name in worker news-worker news-scheduler; do
    if pid_alive "$name"; then
      printf '%-16s \033[0;32m%-10s\033[0m\n' "$name" 运行中
    else
      printf '%-16s \033[0;31m%-10s\033[0m\n' "$name" 已停止
    fi
  done
}

# ── 主流程 ──────────────────────────────────────────────────

main() {
  local action=${1:-status}; shift || true
  load_env
  mkdir -p "$RUN_DIR" "$LOG_DIR"

  case "$action" in
    start)
      local targets=("$@")
      [[ ${#targets[@]} -eq 0 ]] && targets=("${ALL_SERVICES[@]}")
      for s in "${targets[@]}"; do "start_${s//-/_}"; done
      ;;
    stop)
      local targets=("$@")
      if [[ ${#targets[@]} -eq 0 ]]; then
        # 逆序停止：先应用后基础设施
        targets=(news-scheduler news-worker frontend goserver worker python qdrant neo4j redis mysql)
      fi
      for s in "${targets[@]}"; do
        case "$s" in
          mysql) stop_mysql ;;
          redis) stop_redis ;;
          neo4j) stop_neo4j ;;
          *) stop_generic "$s" ;;
        esac
      done
      ;;
    restart) main stop "$@"; main start "$@" ;;
    status)  status ;;
    logs)    [[ -n ${1:-} ]] || die "用法: dev.sh logs <服务>"; tail -f "$LOG_DIR/$1.log" ;;
    *)       die "未知操作: $action（可用: start stop restart status logs）" ;;
  esac
}

main "$@"
