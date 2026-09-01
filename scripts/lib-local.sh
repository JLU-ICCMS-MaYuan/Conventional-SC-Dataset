#!/usr/bin/env bash
# 本地开发环境共享定义。由 setup-local.sh / dev.sh / migrate-from-docker.sh 引用。
# 单一数据源：所有路径、端口、二进制位置只在此处定义一次。

set -euo pipefail

# ── 仓库与数据根目录 ────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$REPO_ROOT/.data"
LOCAL_DIR="$REPO_ROOT/.local"
RUN_DIR="$LOCAL_DIR/run"
LOG_DIR="$LOCAL_DIR/log"

# ── conda 环境 ──────────────────────────────────────────────
CONDA_ROOT="${CONDA_ROOT:-$HOME/miniconda3}"
PY_ENV="$CONDA_ROOT/envs/sc-wiki"           # 应用 Python 依赖
INFRA_ENV="$CONDA_ROOT/envs/sc-wiki-infra"  # mysqld / redis-server / openjdk
PY_BIN="$PY_ENV/bin"
INFRA_BIN="$INFRA_ENV/bin"

# ── 本地安装的服务 ──────────────────────────────────────────
NEO4J_HOME="$LOCAL_DIR/neo4j"
QDRANT_BIN="$LOCAL_DIR/bin/qdrant"
GO_ROOT="$HOME/.local/go"
GO_BIN="$GO_ROOT/bin/go"
GOSERVER_BIN="$LOCAL_DIR/bin/goserver"

# ── 端口 ────────────────────────────────────────────────────
# 宿主机 3306 已被系统级 MySQL 8.0 (/usr/sbin/mysqld) 占用，本项目用 3307。
MYSQL_PORT=3307
REDIS_PORT=6379
NEO4J_BOLT_PORT=7687
NEO4J_HTTP_PORT=7474
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
PYTHON_PORT=8000
GOSERVER_PORT=8080
VITE_PORT=5173

# MySQL socket 与配置：必须与系统 MySQL 完全隔离。
# /etc/mysql/my.cnf 含 user=mysql 与 log_error=/var/log/mysql/error.log，
# 以普通用户启动会直接失败，故所有 mysql* 命令强制 --defaults-file。
MYSQL_CNF="$LOCAL_DIR/my.cnf"
MYSQL_SOCK="$RUN_DIR/mysql.sock"

# ── 版本 ────────────────────────────────────────────────────
GO_VERSION=1.25.14
QDRANT_VERSION=1.19.0

# ── 输出辅助 ────────────────────────────────────────────────
info()  { printf '\033[0;36m==>\033[0m %s\n' "$*"; }
ok()    { printf '\033[0;32m  ✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[0;33m  !\033[0m %s\n' "$*" >&2; }
die()   { printf '\033[0;31m  ✗\033[0m %s\n' "$*" >&2; exit 1; }

# 加载 .env 到环境变量。backend/database.py 与 goserver 都从 os.environ 读取，
# 不能只依赖 pydantic 的 env_file。
load_env() {
  local f="$REPO_ROOT/.env"
  [[ -f "$f" ]] || die "缺少 $f，请先执行 scripts/setup-local.sh"
  set -a
  # shellcheck disable=SC1090
  . "$f"
  set +a
}

# 端口是否已被监听
port_busy() {
  ss -ltn 2>/dev/null | grep -q ":$1[[:space:]]"
}

# 等待条件成立，超时返回 1。用法: wait_for <秒数> <描述> <命令...>
wait_for() {
  local timeout=$1 desc=$2; shift 2
  local i=0
  while (( i < timeout )); do
    if "$@" >/dev/null 2>&1; then return 0; fi
    # 用 ++i 而非 i++：后缀形式返回自增前的值，i=0 时返回 1，
    # 在 set -e 下被当作命令失败并直接中断脚本。
    sleep 1; ((++i))
  done
  warn "等待 $desc 超时（${timeout}s）"
  return 1
}

# 读取 pid 文件并判断进程是否存活
pid_alive() {
  local f="$RUN_DIR/$1.pid"
  [[ -f "$f" ]] || return 1
  local p; p=$(cat "$f" 2>/dev/null) || return 1
  [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null
}

# 显式 -uroot：否则会以当前系统用户 mayuan 连接。ping 恰好在 access denied 时
# 也返回 0，但 shutdown 必须有 root 权限，统一带上避免踩坑。
# </dev/null：这两个客户端在非交互场景下会等待 stdin。
mysql_cli()   { "$INFRA_BIN/mysql" --defaults-file="$MYSQL_CNF" "$@"; }
mysql_admin() { "$INFRA_BIN/mysqladmin" --defaults-file="$MYSQL_CNF" -uroot "$@" </dev/null; }
