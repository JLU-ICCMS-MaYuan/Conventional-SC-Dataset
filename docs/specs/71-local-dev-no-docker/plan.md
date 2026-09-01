# 本地化开发环境：彻底移除 Docker 依赖

## 目标

所有服务跑在宿主机上，改代码立即生效，不再产生任何镜像/容器/构建缓存。
数据统一存放 `/home/mayuan/code/SC-Wiki/.data`。Python 环境使用已存在的 conda `sc-wiki`。

## 可行性验证结论（已实测，非推测）

| 组件 | 方案 | 验证结果 |
|---|---|---|
| MySQL 8.4.2 | conda-forge `mysql-server` | ✅ 已装入 `sc-wiki-infra` |
| Redis 8.10.1 | conda-forge `redis-server` | ✅ 已装入 `sc-wiki-infra` |
| OpenJDK 21 | conda-forge `openjdk` | ✅ 已装入 `sc-wiki-infra` |
| Neo4j 5.26.29 | 从 `neo4j:5` 镜像提取 164MB 纯 Java 应用 | ✅ 启动成功，`cypher-shell` 查询通过 |
| Qdrant 1.19.0 | GitHub musl 静态二进制（经 gh-proxy.com） | ✅ `/readyz` 返回 `all shards are ready` |
| Go 1.25.14 | aliyun 镜像 tarball → `~/.local/go` | ✅ `goserver` 编译通过，增量编译 0.9s |
| Python 依赖 | `sc-wiki` 环境 pip 升级 | ✅ dry-run 通过，41 个包待装 |

### 两个绕不开的实测障碍及对策

1. **Neo4j 官方源全部 403**（`dist.neo4j.org`、`debian.neo4j.com`、aliyun/tuna/ustc/tencent/huawei 镜像均不可用，
   带完整浏览器头仍被 CDN 地域封锁）。唯一可行路径是从已有 `neo4j:5` 镜像提取。
   提取是一次性动作，完成后镜像即可删除，不构成长期 Docker 依赖。
   注意：镜像内 `data`/`logs` 是指向 `/data`、`/logs` 的符号链接，必须替换为真实目录，否则 log4j 初始化失败。

2. **MySQL 版本降级**：Docker 端 8.4.11 → 本地 8.4.2。MySQL 拒绝打开高版本 datadir，
   物理拷贝 `/var/lib/mysql` 必定失败。必须走 `mysqldump` 逻辑导出（已验证：221KB，35 张表）。

## 最终架构

```
本地进程（全部 conda / 二进制，无容器）
├─ mysqld        127.0.0.1:3307   sc-wiki-infra
├─ redis-server  127.0.0.1:6379   sc-wiki-infra
├─ neo4j         127.0.0.1:7687   .local/neo4j + sc-wiki-infra 的 jdk21
├─ qdrant        127.0.0.1:6333   .local/bin/qdrant
├─ uvicorn       127.0.0.1:8000   sc-wiki 环境，--reload
├─ rq worker                       sc-wiki 环境
├─ goserver      127.0.0.1:8080   air 风格热重载（0.9s 增量编译）
└─ vite          127.0.0.1:5173   ← 浏览器入口，HMR
```

MySQL 用 3307：宿主机 3306 已被一个系统级 MySQL 8.0 占用（`/usr/sbin/mysqld`，非本项目）。

请求链路：浏览器 → vite:5173 →（`/api` 代理）→ goserver:8080 →（NoRoute 反代）→ uvicorn:8000。
两段代理都是现成逻辑，无需改代码：`frontend/vite.config.ts:31-39`、`goserver/main.go:207-218`。

## `.data/` 与 `.local/` 布局

```
.data/                          # 已在 .gitignore:85
├── mysql/                      # datadir（mysqld --initialize-insecure 重建）
├── redis/                      # dump.rdb + appendonly
├── neo4j/{data,logs}
├── qdrant/{storage,snapshots}  # 两个都要，缺 snapshots 会 panic exit 101（实测）
├── uploads/ upload_PDFs/ parsed_markdown/
├── review_artifacts/ clean_results/ avatars/
└── prop_name_ai_cache.json

.local/                         # 需新增到 .gitignore
├── neo4j/                      # 从镜像提取的 164MB
├── bin/qdrant                  # 89MB 静态二进制
└── run/                        # pid 与日志
```

Go 装到 `~/.local/go`（仓库外，避免污染工作区）。

## 新增文件

| 文件 | 作用 |
|---|---|
| `scripts/setup-local.sh` | 一次性安装：conda infra 环境、提取 Neo4j、下载 Qdrant/Go、装 Python 依赖、建目录骨架 |
| `scripts/migrate-from-docker.sh` | 一次性迁移：MySQL 逻辑导出导入、Neo4j/Qdrant/Redis/app 数据拷出 |
| `scripts/dev.sh` | 启停编排：`start` / `stop` / `status` / `logs`，含健康等待与端口占用检查 |
| `scripts/goserver-watch.sh` | Go 热重载：`watchfiles` 监听 `goserver/**.go` → 重新编译并重启 |
| `.env` | 全部 host 改 `127.0.0.1`，MySQL 端口 3307，`SC_WIKI_DATA_DIR` 指向 `.data` 绝对路径 |
| `Makefile` | `make setup` / `migrate` / `start` / `stop` / `status` / `clean-docker` |

## 修改的现有文件

- `docker/requirements.txt` — 加 `watchfiles`（uvicorn 非 `[standard]`，`--reload` 缺它跑不了；Go 热重载也复用它）
- `.gitignore` — 补 `.local/`
- `docker/.env.example` — 同步本地开发示例值

**不改任何 `backend/` 或 `goserver/` 源码。** 所有连接地址本来就走环境变量：
`backend/rag/tools/neo4j.py:21`、`backend/rag/config.py:17-28`、`goserver/config/config.go:29-42`。

## 数据迁移（约 1.2GB）

| 卷 | 大小 | 方式 |
|---|---|---|
| `mysql_data_dev` | 225.7MB | **mysqldump 逻辑导出**（8.4.11→8.4.2 降级，不能物理拷） |
| `neo4j_data_dev` | 541.1MB | 物理拷贝（版本相同 5.26.29） |
| `qdrant_storage_dev` | 386.1MB | 物理拷贝（版本相同 1.19.0） |
| `redis_data_dev` | 41.1MB | 物理拷贝（RDB 向前兼容 7.4→8.10） |
| `upload_pdfs_dev` 等 | ~6MB | 物理拷贝 |

卷内文件属主是 `999:999` / `7474:7474`，宿主机 chown 需 root，所以在一次性 alpine 容器里
`cp -a` + `chown -R 1000:1000`。**迁移期间原卷全部保留不删。**

## 空间回收（最后一步，逐条确认后执行）

```
docker compose -f dev.yaml down
docker builder prune -f      # ~6GB   构建缓存
docker container prune -f    # ~541MB 死容器
docker image prune -a -f     # ~19GB  所有镜像
docker volume prune -f       # ~4.4GB 仅在新栈验证通过后
```
合计约 30GB。WSL 的 `ext4.vhdx` 不会自动缩小，Windows 侧需 `wsl --shutdown` + `Optimize-VHD`。

注：根分区已在本次会话期间从 251G 扩到 1007G（当前 208G/1007G，22%），空间压力已缓解，
但清理仍有价值。

## 明确的取舍

- `news-worker` / `news-scheduler` 默认不启动。日常改前后端用不上，需要时单独跑（YAGNI）。
- 保留 `docker/` 目录下的 Dockerfile 与 compose 文件，它们是生产部署产物，与本地开发无关。
- `sc-wiki-infra` 独立于 `sc-wiki`：mysql/redis/jdk 与 Python 依赖混装会迫使 conda 把
  `python` 从 `pkgs/main` 换成 `conda-forge` 版本，危及 `sc-wiki` 里已有的 161 个包（dry-run 实测）。

## 验证方式

1. `make start` 后逐个查四个基础服务：`mysqladmin ping`、`redis-cli ping`、
   `cypher-shell 'RETURN 1'`、`curl :6333/readyz`
2. `curl :8000/health` 与 `curl :8080/health`
3. 浏览器 `localhost:5173` 登录一次（验证 MySQL 数据 + JWT）
4. 改一行 `backend/api/*.py` → uvicorn 自动重启；改一行 `.tsx` → 浏览器 HMR；
   改一行 `goserver/*.go` → 1 秒内重编译重启
5. 打开知识图谱页（Neo4j），跑一次搜索（Qdrant），确认数据完整
6. 迁移后核对行数：`periodic_table_elements` 118、`news_feed_items` 72、`users` 3
