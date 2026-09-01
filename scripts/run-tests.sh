#!/usr/bin/env bash
# 本地跑测试。替代此前"挂载仓库的一次性 Docker 容器"方式。
#
#   scripts/run-tests.sh          后端 pytest
#   scripts/run-tests.sh go       goserver 单元测试
#   scripts/run-tests.sh frontend 前端 vitest

. "$(dirname "${BASH_SOURCE[0]}")/lib-local.sh"

load_env
cd "$REPO_ROOT"

case "${1:-backend}" in
  backend)
    info "后端 pytest"
    exec "$PY_BIN/python" -m pytest backend/tests -q "${@:2}"
    ;;
  go)
    info "goserver 测试"
    export PATH="$GO_ROOT/bin:$PATH"
    export GOPATH="${GOPATH:-$HOME/.local/gopath}"
    export GOCACHE="${GOCACHE:-$HOME/.cache/go-build}"
    export GOPROXY="${GOPROXY:-https://goproxy.cn,direct}"
    cd goserver && exec go test ./... "${@:2}"
    ;;
  frontend)
    info "前端 vitest"
    cd frontend && exec npm run test:upload-ui -- "${@:2}"
    ;;
  *)
    die "未知目标: $1（可用: backend go frontend）"
    ;;
esac
