#!/usr/bin/env bash
# goserver 热重载：监听 goserver/**/*.go，变更时重新编译并重启。
# 增量编译实测约 0.9 秒，复用 Python 环境已有的 watchfiles，无需引入 air。
#
# watchfiles 自身负责在文件变更时终止并重新执行目标命令，
# 因此目标命令只需"编译 + exec 服务"，无需手工管理子进程 pid。

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

load_env
mkdir -p "$LOG_DIR"

# --filter python 只匹配 .py，此处需要 .go，故用默认过滤器并显式忽略产物目录。
exec "$PY_BIN/watchfiles" \
  --ignore-paths "$REPO_ROOT/goserver/cache" \
  "bash '$REPO_ROOT/scripts/goserver-run.sh'" \
  "$REPO_ROOT/goserver"
