# SC-Wiki 本地开发。所有服务跑在宿主机，不依赖 Docker。
#
#   make setup     一次性安装（conda 环境、Neo4j、Qdrant、Go、Python 依赖）
#   make migrate   从 Docker 卷迁移数据到 .data/
#   make start     启动全部服务
#   make stop      停止全部服务
#   make status    查看状态
#   make logs S=python   跟踪某服务日志

.PHONY: setup migrate start stop restart status logs test test-go clean-docker

setup:
	@bash scripts/setup-local.sh

migrate:
	@bash scripts/migrate-from-docker.sh

start:
	@bash scripts/dev.sh start

stop:
	@bash scripts/dev.sh stop

restart:
	@bash scripts/dev.sh restart

status:
	@bash scripts/dev.sh status

# 用法: make logs S=python
logs:
	@bash scripts/dev.sh logs $(or $(S),python)

test:
	@bash scripts/run-tests.sh

test-go:
	@bash scripts/run-tests.sh go

# 清理 Docker 占用的空间。破坏性操作，只打印命令，不自动执行。
clean-docker:
	@echo "以下命令会删除 Docker 资源。只打印不执行，请逐条确认后手动运行。"
	@echo
	@echo "── 可安全执行（仅影响重建速度）──"
	@echo "  docker builder prune -f      # 构建缓存"
	@echo "  docker container prune -f    # 已退出容器"
	@echo "  docker image prune -a -f     # 所有未被使用的镜像"
	@echo
	@echo "── 不可恢复：删除数据卷 ──"
	@echo "  docker volume prune -f       # 迁移前的原始数据备份，删除后无法回退"
	@echo
	@echo "数据卷是本地化迁移前的唯一备份（MySQL/Neo4j/Qdrant 原始数据）。"
	@echo "建议本地环境稳定运行一两周后再执行 volume prune。"
	@echo
	@echo "当前占用："
	@docker system df 2>/dev/null || echo "  (Docker 未运行)"
