# 部署与运行时

## 功能说明

说明 SC-Wiki 的生产 Docker 部署与本地开发运行时两条链路：服务组成、配置入口、数据挂载和启动边界。本文不替代部署包中的数据导入操作说明。

## 当前行为

### 生产：Docker Compose

- 生产编排文件为 `docker/compose.yaml`，包含 frontend、goserver、python、worker、mysql、redis、neo4j、qdrant 和 grobid 服务；GROBID 通过 `/api/isalive` 健康检查后才允许 Python/Worker 启动。
- frontend 使用 Nginx 提供前端静态资源并反向代理；Go 服务提供主要公开 API；未匹配的 Python 能力通过 Go 转发到 Python 服务。
- Go 服务挂载 `graph.json`、`htsc2025.json`、`clean_results` 和持久化头像目录 `/data/avatars`；Python/Worker 服务挂载上传文件、富化结果和属性映射缓存，并通过 `GROBID_URL=http://grobid:8070` 调用引用解析服务。
- MySQL、Redis、Neo4j、Qdrant 和 GROBID 使用 Docker volume 或数据目录持久化。服务通过 healthcheck 和 `depends_on` 控制启动顺序。
- 当前仓库只包含 `docker/compose.yaml`；源码构建可分别使用 `docker/*.Dockerfile`，不存在 `docker/compose.dev.yaml`。

### 本地开发：宿主机进程（[Issue #71](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/71)）

- 本地开发的应用服务运行在宿主机，由 `scripts/dev.sh` 编排，入口为 `Makefile`（`make start` / `stop` / `status` / `logs`）。GROBID 是唯一容器化例外，固定使用 `lfoppiano/grobid:0.8.1` 并仅绑定 `127.0.0.1:8070`，避免本地维护 Java 模型。
- 请求链路为浏览器 → Vite 5173 →（`/api` 代理）→ goserver 8080 →（未匹配路由反代）→ uvicorn 8000。两段代理均为既有实现，本地化未修改 `backend/` 与 `goserver/` 源码。
- 三个应用服务支持热重载：前端 Vite HMR、Python `uvicorn --reload`、goserver 由 `watchfiles` 触发重编译（增量约 1 秒）。Go 编译失败时保留旧进程继续服务。`rq worker` 无热重载，改队列任务代码须手动重启。
- 四个基础服务来自本机安装而非容器：MySQL 8.4.2、Redis 8.10.1 与 Neo4j 所需的 OpenJDK 21 均来自 conda 环境 `sc-wiki`；Neo4j 5.26.29 与 Qdrant 1.19.0 为 `.local/` 下的独立安装。应用 Python 依赖也使用该环境。
- MySQL 监听 3307 而非 3306：宿主机 3306 已被与本项目无关的系统级 MySQL 占用。
- 全部数据存放于仓库内 `.data/`（四个数据库的数据目录、上传文件、解析产物、头像），运行时产物在 `.local/`（二进制、MySQL 配置、pid、日志）。两者均已 gitignore。
- `make start` 默认启动 `news-worker` 与 `news-scheduler`；两者分别消费资讯队列和检查资讯日程，Worker 在 Redis 连接异常后重建连接继续运行。
- 测试可在宿主机直接运行（`scripts/run-tests.sh`，含 backend / go / frontend 三目标），不再需要挂载仓库的一次性容器。
- 使用说明与实施过程中的环境约束记录见 `docs/local-dev.md`。

## 工作流程

### 生产部署

1. 准备 Compose 读取的 `.env`，填写数据库、JWT、Neo4j、LLM、Embedding 和 SMTP 配置；SMTP 至少需要主机与发件人，账号密码按服务商要求提供。
2. 准备 `data/` 下的图谱快照、外部数据、上传目录、富化结果和 Qdrant 存储。
3. 使用 `docker compose -f docker/compose.yaml up -d` 启动服务；首次部署的数据导入和 Neo4j dump 恢复遵循 `docker/deploy/README.md`。
4. 通过 frontend 入口访问站点；Go 的 `/health` 和 Python/RAG 健康接口用于分别核验服务状态。

### 本地开发

1. `make setup` 一次性安装：在既有 conda 环境 `sc-wiki` 安装 MySQL、Redis、OpenJDK 与 Python 依赖，安装 Neo4j 与 Qdrant 到 `.local/`，下载 Go 工具链到 `~/.local/go`，并建立 `.data/` 目录骨架与 MySQL 配置。
2. `make migrate` 从既有 Docker 卷迁移数据（仅首次）。原卷保持只读，不删除不修改。
3. `make start` 启动全部服务，按依赖顺序逐个等待健康检查通过。命令幂等，已运行的服务会跳过。
4. 浏览器访问 `http://127.0.0.1:5173`。`make status` 查看各服务状态，`make logs S=<服务>` 跟踪日志。

### 本地改动如何进入 Docker 部署

本地开发不使用 nginx，前端入口是 Vite dev server。这不影响改动进入生产镜像 —— 两者是无关的两件事：

- `docker/frontend.Dockerfile` 先 `COPY frontend/ .` 拷入**源码**，再在镜像内执行 `npm run build`（即 `tsc -b && vite build`）。nginx 拿到的是该次构建的新产物，不持有任何代码副本，也不参与编译。
- 因此在 Vite 中改的每一行前端代码，重建镜像时都会被编译进去。只有改 `docker/nginx.conf` 本身才需要关注 nginx。
- 本地不用 nginx 的原因是它与热重载互斥：nginx 提供的是 `vite build` 的已构建产物，而热重载的前提是不构建、由 Vite 按需转译源文件。确定前端入口必须是 Vite 后，nginx 剩下的 `/api` 代理职责已由 `frontend/vite.config.ts` 承担，再叠一层即为冗余。

真实差异不是「改动没进去」，而是**同一份代码在两条链路下行为可能不同**，且方向是本地比生产宽松（风险为「本地能用、生产不能用」）：

| 差异项 | 生产 | 本地 | 说明 |
| --- | --- | --- | --- |
| `client_max_body_size` | 50M / 51M | 无上限 | 本地不会触发体积拒绝 |
| `proxy_request_buffering off` | 有 | 无 | 影响大文件上传的流式行为 |
| `proxy_set_header Accept-Encoding ""` | 有 | 无 | 影响响应压缩链路，曾致上传响应 JSON 截断 |
| `removeHeavyPreloads` 插件、`manualChunks` 分包 | 生效 | 不生效 | 仅构建期生效，dev 模式不走，故首屏预取与 chunk 划分问题本地不可见 |

上表前三项只在改动上传相关功能时才有实际意义；第四项影响首屏加载表现。当前的处置是先不引入额外机制，把这些差异作为已知观察项记录（见「已知问题」）。若日后需要收敛，两条候选路径是：新增一个只跑生产构建、不产镜像的校验命令（可覆盖类型错误、构建期插件与依赖缺失等多数「本地好使、镜像挂掉」的情形）；或把 nginx 置于 Vite 之前而非替代之，以复现上表前三项配置，代价是多一层调试面且 HMR 的 WebSocket 经代理偶有连接问题。

## 约束

- `docker/compose.yaml` 依赖预置镜像和外部数据目录，不等同于从空目录自动构建完整数据集。
- RAG 需要 Qdrant、RAG 数据库、Embedding 和 LLM 配置；主业务数据库可用不代表 RAG 可用。
- 旧 Neo4j 图谱、`graph.json` 快照和 MySQL 数据的同步时机不由 Compose 自动解决；Issue #81 的论文引用图直接由 MySQL 查询，不需要 Neo4j 同步。
- 密钥只能通过环境变量注入，文档不记录实际凭据。Go 邮件配置支持 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`/`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM` 和 `SMTP_TLS_MODE`。
- `AVATAR_DIR` 默认为数据目录下 `avatars`，Compose 固定为 `/data/avatars` 并挂载宿主 `docker/data/avatars`；部署备份需包含该目录。
- `docker/deploy/README.md` 中的镜像标签、归档文件和导入命令属于交付包说明，发布前需要按实际归档核验。
- 本地开发环境只使用 conda 环境 `sc-wiki`；其 Python、MySQL、Redis 和 OpenJDK 包均由 conda 统一管理。
- 本地 MySQL 客户端命令必须带 `--defaults-file`：系统 `/etc/mysql/my.cnf` 含 `user = mysql` 与指向 `/var/log/mysql/` 的错误日志路径，以普通用户启动会失败。
- 本地开发链路不含 nginx，`docker/nginx.conf` 中的 `client_max_body_size`、`proxy_request_buffering off` 与 `Accept-Encoding` 清空均不生效；`vite build` 期生效的 `removeHeavyPreloads` 与 `manualChunks` 在 dev 模式下同样不走。这不影响改动进入镜像（镜像内会重新构建源码），但同一份代码在两条链路下的上传与首屏行为可能不同，详见「本地改动如何进入 Docker 部署」。
- 当前 WSL `networkingMode=mirrored` 本地开发环境中，UFW 必须保持停止且禁止开机启动。宝塔安装器启用 UFW 并设置默认拒绝策略后，`loopback0` 上的 localhost TCP 流量会被拦截，导致 VS Code Remote WSL 和 Windows 访问本地服务失败。该约束只适用于当前 WSL 本地开发环境，不改变生产服务器的防火墙策略（[Issue #89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)）。

## 代码与测试

- `docker/compose.yaml`
- `docker/nginx.conf`
- `docker/frontend.Dockerfile`
- `docker/goserver.Dockerfile`
- `docker/python.Dockerfile`
- `docker/deploy/README.md`
- `goserver/main.go`
- `backend/main.py`
- `Makefile`
- `scripts/lib-local.sh`
- `scripts/setup-local.sh`
- `scripts/dev.sh`
- `scripts/goserver-watch.sh`
- `scripts/goserver-run.sh`
- `scripts/migrate-from-docker.sh`
- `scripts/gen-env.py`
- `scripts/run-tests.sh`
- `docs/local-dev.md`

## 相关变更记录

- [Issue #71](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/71)：本地化开发环境，移除 Docker 依赖（`docs/specs/71-local-dev-no-docker/`）
- [Issue #89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)：WSL mirrored 与宝塔防火墙的本地开发兼容性（[Spec](../../specs/89-local-dev-firewall-compatibility/spec.md)）

## 已知问题

- 交付包中的镜像标签和数据归档是否与当前 Compose 文件一致，待发布前核验。
- 本地直接运行 Go/Python 与 Docker 反向代理链路的接口覆盖仍需按部署环境验证。
- SMTP 服务商连通性、TLS 模式和实际发件能力需要在目标环境验收。
- 本地开发的大文件上传未在缺少 nginx 的链路下验证，行为是否与生产一致待核验。本地无体积上限，生产受 `client_max_body_size` 约束，故超限行为只能在生产链路暴露。
- 首屏预取与 chunk 划分只在 `vite build` 后成立，本地 dev 模式不可见，相关回归需在生产构建产物上核验。
- 尚未引入生产构建校验命令或本地 nginx 层。当前依赖「重建镜像时源码会被重新构建」这一事实保证改动不丢失，两条链路的行为差异作为观察项，暂不额外投入。
- `scripts/migrate-from-docker.sh` 仍需 Docker（用一次性容器读卷）。属一次性脚本，原卷清理后可连同删除。
