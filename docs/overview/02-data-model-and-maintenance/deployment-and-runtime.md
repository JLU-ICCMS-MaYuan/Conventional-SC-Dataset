# 部署与运行时

## 功能说明

说明 SC-Wiki 当前 Docker 部署的服务组成、配置入口、数据挂载和启动边界。本文不替代部署包中的数据导入操作说明。

## 当前行为

- 生产编排文件为 `docker/compose.yaml`，包含 frontend、goserver、python、mysql、redis、neo4j 和 qdrant 七个服务。
- frontend 使用 Nginx 提供前端静态资源并反向代理；Go 服务提供主要公开 API；未匹配的 Python 能力通过 Go 转发到 Python 服务。
- Go 服务挂载 `graph.json`、`htsc2025.json`、`clean_results` 和持久化头像目录 `/data/avatars`；Python 服务挂载上传文件、富化结果和属性映射缓存。
- MySQL、Redis、Neo4j 和 Qdrant 使用 Docker volume 或数据目录持久化。服务通过 healthcheck 和 `depends_on` 控制启动顺序。
- 当前仓库只包含 `docker/compose.yaml`；源码构建可分别使用 `docker/*.Dockerfile`，不存在 `docker/compose.dev.yaml`。

## 工作流程

1. 准备 Compose 读取的 `.env`，填写数据库、JWT、Neo4j、LLM、Embedding 和 SMTP 配置；SMTP 至少需要主机与发件人，账号密码按服务商要求提供。
2. 准备 `data/` 下的图谱快照、外部数据、上传目录、富化结果和 Qdrant 存储。
3. 使用 `docker compose -f docker/compose.yaml up -d` 启动服务；首次部署的数据导入和 Neo4j dump 恢复遵循 `docker/deploy/README.md`。
4. 通过 frontend 入口访问站点；Go 的 `/health` 和 Python/RAG 健康接口用于分别核验服务状态。

## 约束

- `docker/compose.yaml` 依赖预置镜像和外部数据目录，不等同于从空目录自动构建完整数据集。
- RAG 需要 Qdrant、RAG 数据库、Embedding 和 LLM 配置；主业务数据库可用不代表 RAG 可用。
- Neo4j 图谱、`graph.json` 快照和 MySQL 数据的同步时机不由 Compose 自动解决。
- 密钥只能通过环境变量注入，文档不记录实际凭据。Go 邮件配置支持 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`/`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM` 和 `SMTP_TLS_MODE`。
- `AVATAR_DIR` 默认为数据目录下 `avatars`，Compose 固定为 `/data/avatars` 并挂载宿主 `docker/data/avatars`；部署备份需包含该目录。
- `docker/deploy/README.md` 中的镜像标签、归档文件和导入命令属于交付包说明，发布前需要按实际归档核验。

## 代码与测试

- `docker/compose.yaml`
- `docker/nginx.conf`
- `docker/frontend.Dockerfile`
- `docker/goserver.Dockerfile`
- `docker/python.Dockerfile`
- `docker/deploy/README.md`
- `goserver/main.go`
- `backend/main.py`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 交付包中的镜像标签和数据归档是否与当前 Compose 文件一致，待发布前核验。
- 本地直接运行 Go/Python 与 Docker 反向代理链路的接口覆盖仍需按部署环境验证。
- SMTP 服务商连通性、TLS 模式和实际发件能力需要在目标环境验收。
