# Bug 规格：News 自动采集 scheduler 与 worker 部署

**GitHub Issue**：[ #86](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/86)

**创建日期**：2026-09-03

**状态**：已实现，待运行环境验收

## 背景与目标

资讯采集代码已有每天北京时间 08:00 调度、失败重试和独立 `scwiki-news` 队列，但 Docker Compose 未启动 scheduler 和该队列的 Worker。上传 Worker 不消费资讯队列，导致部署环境从不执行自动采集。

本修复将 News scheduler 和 Worker 作为独立 Compose 服务以及本地开发编排服务常驻运行，保证容器或本地开发服务重启后恢复每日自动采集，且不改变上传任务的队列职责。

## 用户场景与验收

### 用户故事 1：部署后持续自动更新资讯（优先级：P1）

运维人员执行通常的 `docker compose up -d` 后，不需要手工运行采集命令，系统会在每天北京时间 08:00 调度资讯采集，并由专用 Worker 执行。

**验收场景**：

1. **假如**迁移完成且 Redis 健康，**当**Compose 启动，**那么**`news-scheduler` 和 `news-worker` 自动运行并在容器重启后恢复。
2. **假如**时间到达每日 08:00 或上次成功早于当日截止时间，**当**scheduler 检查状态，**那么**它只向 `scwiki-news` 入队待采集来源。
3. **假如**上传 Worker 正常运行，**当**资讯任务入队，**那么**上传 Worker 的命令及其队列职责不变，News Worker 独立消费资讯任务。

### 边界与异常场景

- `migrate` 未成功或 Redis 未健康时，资讯服务不得提前启动。
- 任一采集源失败仍由现有调度规则在一小时后重试；本修复不改变该行为。
- 不在本次实施中运行 `docker compose up` 或重启生产容器。

## 需求

- **FR-001**：`docker/compose.yaml` 必须新增 `news-scheduler`，命令为 `python -m backend.news schedule`。
- **FR-002**：`docker/compose.yaml` 必须新增 `news-worker`，命令为 `python -m backend.news worker`，且不得替换或复用上传 Worker。
- **FR-003**：两个服务必须使用既有 Python 镜像，并显式传入 `DATABASE_URL`、`REDIS_URL`、`NEWS_DAILY_HOUR=8`、`NEWS_TIMEZONE=Asia/Shanghai`、`NEWS_INITIAL_DAYS=7`、`NEWS_MAX_PAGES=100`。
- **FR-004**：两个服务必须依赖 `migrate: service_completed_successfully` 与 `redis: service_healthy`，并使用 `restart: unless-stopped`。
- **FR-005**：自动化测试必须核验 Compose 服务命令、环境、依赖、重启策略和上传 Worker 不变；既有调度时间测试必须继续通过。
- **FR-006**：`scripts/dev.sh start` 不带服务参数时必须启动 `news-worker` 和 `news-scheduler`；停止、状态和日志命令必须继续覆盖这两个服务。

## 成功标准

- **SC-001**：`docker compose config` 成功渲染并包含两个 News 服务，均使用已有 Python 镜像、正确命令与运行依赖。
- **SC-002**：配置级测试验证 News Worker 和上传 Worker 不共享命令或队列职责。
- **SC-003**：资讯调度单元测试通过，并证明默认时区在 08:00 触发日调度。
- **SC-004**：本地开发启动脚本的默认服务列表包含两个 News 进程，且其进程命令分别为 `backend.news worker` 和 `backend.news schedule`。

## 假设与依赖

- 现有 Python 镜像已经包含 `backend.news`、RQ、Redis 和采集依赖。
- 生产环境仍通过 `docker compose up -d` 管理服务，环境变量由现有 `.env` 提供。

## 范围外事项

- 资讯采集源、API、数据库表和前端页面。
- 立即启动、停止、重建或部署 Compose 服务。
- 修改上传 Worker 的命令、并发策略或队列。

## 实现记录

- Docker Compose 已新增 `news-scheduler` 和 `news-worker`，分别运行调度命令和 `scwiki-news` 队列 Worker。
- 本地 `scripts/dev.sh start` 的默认服务列表已包含 `news-worker` 和 `news-scheduler`；`make start` 会间接启动它们。
- 已验证 3 个定向 pytest、`bash -n scripts/dev.sh` 和 `docker compose config`。
- 尚未在真实部署环境执行 `docker compose up`，因此生产容器的实际运行状态仍需单独验收。
