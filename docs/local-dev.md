# 本地开发环境

应用服务跑在宿主机，改代码立即生效。GROBID 是唯一例外：它以
`lfoppiano/grobid:0.8.1` 容器运行，并且只绑定 `127.0.0.1:8070`，避免在本机
维护 Java 模型与运行时。

## 快速开始

```bash
make setup     # 一次性安装
make migrate   # 从 Docker 卷迁移数据（仅首次）
make start     # 启动全部服务
```

浏览器打开 http://127.0.0.1:5173

```bash
make status         # 查看各服务状态
make logs S=python  # 跟踪日志（python/goserver/frontend/mysql/neo4j/qdrant/redis/worker）
make stop           # 停止全部
```

## 服务构成

| 服务 | 地址 | 来源 | 热重载 |
|---|---|---|---|
| frontend (vite) | 127.0.0.1:5173 | `frontend/node_modules` | HMR |
| goserver | 127.0.0.1:8080 | `~/.local/go` 编译 | 有（约 1s） |
| python (uvicorn) | 127.0.0.1:8000 | conda `sc-wiki` | 有 |
| worker (rq) | — | conda `sc-wiki` | 无（改队列任务需 `make restart`） |
| mysql | 127.0.0.1:**3307** | conda `sc-wiki-infra` | — |
| redis | 127.0.0.1:6379 | conda `sc-wiki-infra` | — |
| neo4j | bolt://127.0.0.1:7687 | `.local/neo4j` | — |
| qdrant | 127.0.0.1:6333 | `.local/bin/qdrant` | — |
| grobid | 127.0.0.1:8070 | `lfoppiano/grobid:0.8.1` 容器 | — |

请求链路：浏览器 → vite（`/api` 代理）→ goserver →（未命中路由反代）→ uvicorn。

MySQL 用 3307 而非 3306：宿主机 3306 已被一个系统级 MySQL 8.0（`/usr/sbin/mysqld`）占用，
与本项目无关。

`news-worker` / `news-scheduler` 默认不启动，日常开发用不上。需要时：

```bash
bash scripts/dev.sh start news-worker news-scheduler
```

引用解析需要在本地 `.env` 配置：

```bash
GROBID_URL=http://127.0.0.1:8070
```

`make start` 会在启动 Python/Worker 前启动 GROBID；单独维护时可使用
`bash scripts/dev.sh start grobid`、`status` 或 `stop grobid`。首次拉取镜像会占用
较多磁盘和内存，但端口不暴露给局域网。在当前 WSL cgroup 环境中，脚本会为该
容器设置 `JAVA_TOOL_OPTIONS=-XX:-UseContainerSupport`，避免 Java 容器资源探测异常；
该选项不影响生产 Compose。

## 两个 conda 环境

- **`sc-wiki`** — 应用 Python 依赖（FastAPI、pymatgen、rq 等）
- **`sc-wiki-infra`** — mysqld / redis-server / openjdk 21 / mysql 客户端

分开是必要的：把 `mysql-server` 装进 `sc-wiki` 会迫使 conda 将 `python` 从
`pkgs/main` 换成 `conda-forge` 版本，进而重装并可能破坏已有的科学计算包。

## 目录

```
.data/          # 全部数据，已 gitignore
├── mysql/ redis/ neo4j/ qdrant/
├── uploads/ upload_PDFs/ parsed_markdown/
├── review_artifacts/ clean_results/ avatars/
└── prop_name_ai_cache.json

.local/         # 运行时，已 gitignore
├── neo4j/          从 neo4j:5 镜像提取的 Neo4j 5.26.29
├── bin/            qdrant 与编译产出的 goserver
├── my.cnf          MySQL 配置（与系统 MySQL 完全隔离）
├── run/ log/       pid 与日志
└── run-neo4j/      Neo4j 自己的 pid 目录（必须与 run/ 分开，见下）
```

Go 工具链装在仓库外的 `~/.local/go`。

## 测试

```bash
make test              # 后端 pytest
make test-go           # goserver
bash scripts/run-tests.sh frontend
```

不再需要"挂载仓库的一次性 Docker 容器"来跑后端测试。

## 本地改的代码会进入 Docker 部署吗

会。这两件事无关，不用担心「在 vite 里改了但 nginx 里没更新」。

`docker/frontend.Dockerfile` 的做法是先 `COPY frontend/ .` 拷入**源码**，再在镜像内跑
`npm run build`。nginx 拿到的是这次构建的新产物，它不持有代码副本，也不参与编译。
所以你改的每一行前端代码，重建镜像时都会被编译进去。只有改 `docker/nginx.conf`
本身才需要关心 nginx。

本地不用 nginx 是因为它和热重载互斥：nginx 提供的是 `vite build` 的已构建产物，
而热重载的前提恰恰是不构建、由 Vite 按需转译源文件。既然前端入口必须是 Vite，
nginx 剩下的 `/api` 代理职责 `vite.config.ts` 已经在做，再叠一层就是冗余。

### 真正的差异：同一份代码，两种环境行为可能不同

方向是**本地比生产宽松**，所以风险是「本地能用、生产不能用」，不是「改了没生效」。

| 差异项 | 生产 | 本地 |
|---|---|---|
| `client_max_body_size` | 50M / 51M | 无上限 |
| `proxy_request_buffering off` | 有 | 无 |
| `Accept-Encoding` 清空 | 有 | 无 |
| `removeHeavyPreloads` / `manualChunks` | 生效 | 不生效（仅构建期） |

前三项只在改上传相关功能时才有意义；第四项影响首屏加载和 chunk 划分，本地永远看不出来。
`Accept-Encoding` 那条值得留意，因为 `backend/main.py` 装了 `GZipMiddleware`，
压缩行为在两条链路上确实不同 —— 当初加这条就是为了修上传响应 JSON 截断。

当前**不引入额外机制**，把这些差异当观察项。改上传功能或排查首屏性能时，
直接起一次生产 compose 验证，比在本地维护半真半假的 nginx 层更可靠。

日后若要收敛，两条候选路径：加一个只跑生产构建、不产镜像的校验命令
（能覆盖类型错误、构建期插件、依赖缺失等多数「本地好使、镜像挂掉」的情形）；
或把 nginx 放在 Vite **前面**而非替代它（能复现前三项配置，代价是多一层调试面，
且 HMR 的 WebSocket 走代理偶发连接问题）。

## 实施过程中踩到的坑

这些都是实测结果，改动相关配置前值得先读一遍。

**Neo4j 官方源全部返回 403。** `dist.neo4j.org`、`debian.neo4j.com`，以及
aliyun / tuna / ustc / 腾讯 / 华为镜像，带完整浏览器头也一样被 CDN 地域封锁。
因此 `setup-local.sh` 从 `neo4j:5` 镜像提取——它就是个纯 Java 应用。
这是一次性动作，提取完镜像即可删除。

**Neo4j 的 pid 文件会与包装进程的 pid 文件撞名。** 两者都叫 `neo4j.pid`。
放同一目录时 Neo4j 会读到包装进程的 pid，误判"已在运行"并拒绝启动。
故 `server.directories.run` 指向独立的 `.local/run-neo4j/`。

**镜像里的 `data`/`logs` 是符号链接**，指向 `/data`、`/logs`。不替换成真实路径，
log4j 初始化就会失败，且错误信息完全不提符号链接。

**Qdrant 必须同时指定 storage 和 snapshots 路径。** 只给 storage 会
panic 退出（exit 101），日志里的直接线索只有一行 `.qdrant-initialized` 权限警告。

**MySQL 数据不能物理拷贝。** Docker 端是 8.4.11，conda-forge 最高 8.4.2，
MySQL 拒绝打开高版本 datadir。必须走 `mysqldump` 逻辑导出，`migrate-from-docker.sh` 已如此实现。

**所有 mysql 命令必须带 `--defaults-file`。** 系统 `/etc/mysql/my.cnf` 含
`user = mysql` 和 `log_error = /var/log/mysql/error.log`，以普通用户启动会直接失败。

**`redis-cli` 和 `mysqladmin` 在脚本里要重定向 stdin。** 否则等待输入而挂住。

**`mysqladmin ping` 在权限不足时也返回 0**（服务器活着就算通）。健康检查看似正常，
但 `shutdown` 需要 root，故统一显式带 `-uroot`。

**bash 的 `local a=$1 b="$a"` 是陷阱。** 整行会在 `local` 执行前完成展开，
此时 `$a` 尚未赋值，`set -u` 下直接报 unbound variable。必须拆成两行。

## 已知的既有问题（非本次引入）

- `tests/07_researcher_community_forum/news-feed.test.tsx` 中一个用例失败。在干净的 `HEAD` 上同样失败，与本地化无关。
- 数据库里 `papers.knowledge_graph_title` 列已存在但 `alembic_version` 未记录该 revision
  （Docker 库里也一样，说明是手工加的列）。已用 `alembic stamp head` 对齐。
