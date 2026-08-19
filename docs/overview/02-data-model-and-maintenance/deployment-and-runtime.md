# 部署与运行时

## 功能说明

说明 SC-Wiki 当前 Docker 部署的服务组成、配置入口、数据挂载和启动边界。本文不替代部署包中的数据导入操作说明。

## 当前行为

- 生产编排文件为 `docker/compose.yaml`，包含 frontend、goserver、python、mysql、redis、neo4j 和 qdrant 七个服务。
- frontend 使用 Nginx 提供前端静态资源并反向代理；Go 服务提供主要公开 API；未匹配的 Python 能力通过 Go 转发到 Python 服务。
- Go 服务挂载 `graph.json`、`htsc2025.json` 和 `clean_results`；Python 服务挂载上传文件、富化结果和属性映射缓存。
- MySQL、Redis、Neo4j 和 Qdrant 使用 Docker volume 或数据目录持久化。服务通过 healthcheck 和 `depends_on` 控制启动顺序。
- 开发编排使用 `docker/compose.dev.yaml`，从源码构建镜像并将前端暴露在 `8080`。

## 工作流程

1. 准备 `docker/.env.example` 对应的 `.env`，填写数据库、JWT、Neo4j、LLM 和 Embedding 配置。
2. 准备 `data/` 下的图谱快照、外部数据、上传目录、富化结果和 Qdrant 存储。
3. 使用 `docker compose -f docker/compose.yaml up -d` 启动服务；首次部署的数据导入和 Neo4j dump 恢复遵循 `docker/deploy/README.md`。
4. 通过 frontend 入口访问站点；Go 的 `/health` 和 Python/RAG 健康接口用于分别核验服务状态。

## 约束

- `docker/compose.yaml` 依赖预置镜像和外部数据目录，不等同于从空目录自动构建完整数据集。
- RAG 需要 Qdrant、RAG 数据库、Embedding 和 LLM 配置；主业务数据库可用不代表 RAG 可用。
- Neo4j 图谱、`graph.json` 快照和 MySQL 数据的同步时机不由 Compose 自动解决。
- 密钥只能通过环境变量注入，文档不记录实际凭据。
- `docker/deploy/README.md` 中的镜像标签、归档文件和导入命令属于交付包说明，发布前需要按实际归档核验。

## 代码与测试

- `docker/compose.yaml`
- `docker/compose.dev.yaml`
- `docker/.env.example`
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
