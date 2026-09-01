#!/usr/bin/env bash
# 编译并运行 goserver。由 goserver-watch.sh 在每次文件变更后调用。
# 单独执行也可用于快速验证编译是否通过。

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

load_env

export PATH="$GO_ROOT/bin:$PATH"
export GOPATH="${GOPATH:-$HOME/.local/gopath}"
export GOCACHE="${GOCACHE:-$HOME/.cache/go-build}"
export GOPROXY="${GOPROXY:-https://goproxy.cn,direct}"

cd "$REPO_ROOT/goserver"

# 编译到临时名再替换：编译失败时不破坏已有可用二进制。
if ! go build -o "$GOSERVER_BIN.new" . ; then
  warn "编译失败，等待下一次文件变更"
  # 退出码 0：避免 watchfiles 认为命令崩溃而停止监听。
  exit 0
fi
mv -f "$GOSERVER_BIN.new" "$GOSERVER_BIN"

exec "$GOSERVER_BIN"
