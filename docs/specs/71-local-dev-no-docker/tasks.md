# 实施任务：本地化开发环境，移除 Docker 依赖

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：定位根因

- [x] T001 `docker system df -v` 量化占用：镜像 19.8GB（可回收 88%）、
  构建缓存 8.62GB、容器 822MB；根分区 222G/251G
- [x] T002 `docker history sc-wiki-dev-python` 定位大层：`pip install` 996MB +
  `apt-get install build-essential` 336MB
- [x] T003 识别 `docker/python.Dockerfile:13` 的无效优化 —— `apt-get purge`
  与 `pip install` 同层，但编译器是上一层装的，purge 只写 whiteout，336MB 仍在
- [x] T004 区分垃圾来源：三个自建服务产生全部垃圾，四个官方镜像从不重建
- [x] T005 确认两个 dangling 镜像的 `UNIQUE SIZE` 均约 1.76GB —— 各含一份独立
  完整的 pip 安装层，证实「层不可覆盖」

## 阶段 2：可行性实测（先验证再动手）

**目的**：本地化涉及四个数据库两个语言运行时，任一组件不可行则方案作废。
不推测，全部实测。

- [x] T006 [P] conda-forge 查包：`mysql-server` 有 8.4.2、`redis-server` 8.10.1、
  `openjdk` 21 —— 均可用
- [x] T007 [P] 探测 Neo4j 下载源：`dist.neo4j.org`、`debian.neo4j.com`、aliyun、
  tuna、ustc、腾讯、华为镜像**全部 403**，带完整浏览器头亦然
- [x] T008 确认 Neo4j 替代路径：`neo4j:5` 镜像内为纯 Java 应用，`tar` 提取 164MB
- [x] T009 [P] 探测 Qdrant 源：GitHub 直连不可达，`gh-proxy.com` 可用；
  `ghproxy.net`、`hub.gitmirror.com` 不可用
- [x] T010 实测 Qdrant musl 静态二进制独立启动 —— `/readyz` 返回
  `all shards are ready`
- [x] T011 实测 Neo4j + conda openjdk21 启动 —— `Bolt enabled`、`Started`，
  `cypher-shell 'RETURN 1'` 通过
- [x] T012 踩坑：Neo4j 首次启动失败，因镜像内 `data`/`logs` 是指向 `/data`、`/logs`
  的符号链接，log4j 初始化失败且错误信息不提符号链接
- [x] T013 [P] 实测全部 Python 依赖装入独立 venv —— 成功，666MB，
  `backend.main` 可导入
- [x] T014 发现 uvicorn 非 `[standard]` 版本不带 `watchfiles`，`--reload` 需补装
- [x] T015 [P] 实测 Go 工具链：aliyun tarball 可下载，`goserver` 编译通过，
  **增量编译 0.9 秒** —— 热重载可行
- [x] T016 [P] 实测四个官方镜像 bind mount + `--user 1000:1000`：MySQL/Redis/Neo4j
  通过，**Qdrant panic exit 101**
- [x] T017 定位 Qdrant 崩溃原因：还需写 `/qdrant/snapshots`，必须同时挂两个目录
- [x] T018 对比版本差异发现 MySQL 降级：Docker 8.4.11 → 本地 8.4.2，
  datadir 不能物理拷贝
- [x] T019 实测 `mysqldump` 逻辑导出可行 —— 221KB、35 张表
- [x] T020 `sc-wiki` 环境 pip dry-run —— 通过，41 个包待装，无冲突
- [x] T021 检查 `sc-wiki` 现状：Python 3.12.13，已有 161 个包，
  缺 feedparser / langchain-* / langgraph / neo4j
- [x] T022 独立 infra 环境 dry-run 对比：装进 `sc-wiki` 会迫使 conda 把 `python`
  换成 conda-forge 版本 —— 确认必须分环境

## 阶段 3：脚本骨架

- [x] T023 [US2] 新建 `scripts/lib-local.sh`：单一数据源，集中定义路径、端口、
  二进制位置、`load_env`、`wait_for`、`port_busy`、`pid_alive`
- [x] T024 [US3] 新建 `scripts/gen-env.py`：从旧 `.env` 生成本地 `.env`，
  只改写连接地址，密钥不经 shell 不入日志
- [x] T025 生成 `.env` 并校验 —— 16 项透传、8 项补充，MySQL 端口 3307，
  host 全部 127.0.0.1
- [x] T026 [US2] 新建 `scripts/setup-local.sh`：六步幂等安装
- [x] T027 踩坑：发现系统 `/etc/mysql/my.cnf` 含 `user = mysql` 与
  `log_error=/var/log/mysql/error.log`，普通用户启动必失败 → 所有 mysql 命令
  强制 `--defaults-file`
- [x] T028 执行 `setup-local.sh` 并逐项验证六个组件版本

## 阶段 4：运行时编排

- [x] T029 [US2] 新建 `scripts/dev.sh`：`start` / `stop` / `restart` / `status` / `logs`
- [x] T030 [US1] 新建 `scripts/goserver-watch.sh` 与 `scripts/goserver-run.sh`：
  watchfiles 监听 → 编译 → exec；编译失败保留旧进程
- [x] T031 简化 goserver 热重载设计：watchfiles 自身负责终止与重启目标命令，
  删掉手工管理子进程 pid 的初版实现
- [x] T032 [US2] 新建 `Makefile`：`setup` / `migrate` / `start` / `stop` /
  `status` / `logs` / `test` / `clean-docker`
- [x] T033 [US2] 新建 `scripts/run-tests.sh`：backend / go / frontend 三目标，
  取代「挂载仓库的一次性容器」

## 阶段 5：逐个服务启动与踩坑修复

- [x] T034 启动 MySQL —— 通过
- [x] T035 修复 `mysqladmin` / `redis-cli` 在脚本中等待 stdin 而挂住 —— 加 `</dev/null`
- [x] T036 修复 `mysqladmin ping` 未带 `-uroot`：ping 在 access denied 时也返回 0
  故检查看似正常，但 `shutdown` 需要 root，统一显式带上
- [x] T037 启动 Redis —— 通过；`appendonly no` 避免 AOF 增量文件损坏
- [x] T038 启动 Qdrant —— 通过（storage 与 snapshots 均显式指定）
- [x] T039 Neo4j 启动失败：`Neo4j is already running (pid:...)`
- [x] T040 定位 T039 根因：Neo4j 自己也写 `neo4j.pid`，与 dev.sh 包装进程的 pid 文件
  同名同目录，Neo4j 读到包装进程 pid 而误判 → `server.directories.run` 指向独立
  `.local/run-neo4j/`
- [x] T041 启动 Neo4j 并验证 `.env` 密码生效 —— `cypher-shell` 认证通过

## 阶段 6：数据迁移

- [x] T042 [US3] 新建 `scripts/migrate-from-docker.sh`：原卷只读挂载，
  在 alpine 容器内 `cp -a` + `chown -R 1000:1000`
- [x] T043 停止 Docker 的 neo4j / qdrant 以保证拷贝一致性；MySQL 保持运行供导出
- [x] T044 [US3] MySQL 逻辑导出导入 —— 35 张表，并创建 `scwiki` 业务账号
  （localhost 与 127.0.0.1 两个 host）
- [x] T045 核对 MySQL 行数与 Docker 侧逐项一致 —— 118 / 87 / 72 / papers 1 /
  superconductors 9 / users 3
- [x] T046 [US3] 迁移 Neo4j 517MB、Qdrant 369MB；先清空此前启动测试产生的空库
- [x] T047 [US3] 迁移 Redis 仅取 RDB（AOF 增量文件已损坏）
- [x] T048 [US3] 迁移应用数据：upload_PDFs、parsed_markdown、review_artifacts、
  clean_results、uploads、avatars、prop_name_ai_cache.json
- [x] T049 核对 Neo4j 1 个 Paper 节点、Qdrant 1 个点 —— 与 MySQL 的 papers=1
  交叉印证，确认非部分拷贝

## 阶段 7：应用层启动

- [x] T050 Python 启动失败：alembic `Duplicate column name 'knowledge_graph_title'`
- [x] T051 判定 T050 为**既有问题**：Docker 库中该列同样已存在且 `alembic_version`
  未记录该 revision，说明是手工加的列，非迁移引入 → `alembic stamp head` 对齐
- [x] T052 启动 python（`--reload`，仅监听 `backend/` 避免 `.data` 写入触发重启）
- [x] T053 启动 worker 与 goserver
- [x] T054 停止整个旧 Docker 栈，避免端口争用
- [x] T055 启动 frontend

## 阶段 8：验证

- [x] T056 [US2] `dev.sh status` —— 8 个服务全部运行中
- [x] T057 [US1] 全链路：python `/health`、goserver `/health`、
  vite→go 知识图谱、vite→go MySQL 检索、vite→go→python 反代 200
- [x] T058 [US1] Go 热重载 —— 改 `main.go` 后 pid 1546962 → 1552510，还原
- [x] T059 [US1] Python 热重载 —— 日志出现
  `WatchFiles detected changes in 'backend/main.py'`，还原
- [x] T060 后端 pytest —— 116 passed
- [x] T061 goserver 测试 —— 全部 package ok
- [x] T062 前端 vitest —— 109/110；在干净 `HEAD` worktree 中复现同一失败，
  确认为既有问题
- [x] T063 [US2] 全量停止失败，退出码 1，停在第 3 个服务
- [x] T064 定位 T063 根因：`((i++))` 返回自增**前**的值，`i=0` 时返回 1，
  `set -e` 视为失败并中断 → 全部改为 `((++i))`
- [x] T065 定位并修复 `local name=$1 f="$RUN_DIR/$name.pid"`：bash 在 `local`
  执行前完成整行展开，`$name` 尚未赋值，`set -u` 下报 unbound variable → 拆两行
- [x] T066 [US2] 全量停止 —— 10 个服务干净退出，端口与进程无残留

## 阶段 9：收尾

- [x] T067 `.gitignore` 补 `.local/`；确认 `.data/`、`.env` 已忽略
- [x] T068 `docker/requirements.txt` 加 `watchfiles==1.2.0`
- [x] T069 新建 `docs/local-dev.md`：使用说明 + 全部踩坑记录 + 既有问题
- [x] T070 用户执行 Docker 清理 —— Images/Containers/Build Cache 归零
- [x] T071 修正回收量预估偏差：实际 1.46GB 而非预估 25GB。原因是 daemon 在会话
  中途重启已自行清掉构建缓存与 dangling 镜像，且验证过程重新拉过官方镜像
- [x] T072 `Makefile` 的 `clean-docker` 加入 `docker volume prune -f`，
  单独分组标为「不可恢复」，去掉写死的容量数字改为实时 `docker system df`
- [x] T073 创建 Issue、解决 #70 编号冲突、撰写 spec.md 与 tasks.md
- [ ] T074 回写 `docs/overview/`

## 需求覆盖对照

| 需求 | 实施任务 | 验证 |
|------|------|------|
| FR-001（基础服务本地化） | T026、T034-T041 | T056 |
| FR-002（三服务热重载） | T030、T052 | T058、T059 |
| FR-003（数据入 .data） | T026、T042-T048 | T067 |
| FR-004（用 sc-wiki 环境） | T020、T026 | T060 |
| FR-005（单命令幂等启停） | T029、T032 | T056、T066 |
| FR-006（健康检查等待） | T023、T029 | T056 |
| FR-007（原卷只读） | T042 | 迁移后卷仍存在 3.589GB |
| FR-008（按版本选迁移方式） | T018、T044、T046、T047 | T045、T049 |
| FR-009（mysql 配置隔离） | T027、T036 | T034 |
| FR-010（编译失败保留旧进程） | T030 | 代码审查 |
| FR-011（宿主机跑测试） | T033 | T060-T062 |
| FR-012（清理只打印） | T032、T072 | T070 |
| SC-001 | T034-T041 | 通过 |
| SC-002 | T044-T049 | 行数逐项一致 |
| SC-003 | T057 | 通过 |
| SC-004 | T058 | pid 已变 |
| SC-005 | T059 | 日志确认 |
| SC-006 | T060 | 116 passed |
| SC-007 | T061 | 全部 ok |
| SC-008 | T062 | 既有失败，非新增 |
| SC-009 | T066 | 无残留 |
| SC-010 | T070 | 三项归零 |

## 后续操作指引

### 日常开发

```bash
make start              # 启动全部（幂等，已运行的跳过）
make status             # 查看状态
make logs S=python      # 跟踪日志
make stop               # 停止全部
```

浏览器入口 http://127.0.0.1:5173

### 改代码后是否需要重启

| 改动 | 操作 |
|---|---|
| `frontend/src/**` | 无需操作，HMR 自动生效 |
| `backend/**` | 刷新页面（uvicorn 自动重启 1-2s） |
| `goserver/**/*.go` | 刷新页面（自动重编译约 1s） |
| `.env` | `make restart` |
| `docker/requirements.txt` | pip 安装后 `dev.sh restart python worker` |
| `frontend/package.json` | npm 安装后 `dev.sh restart frontend` |
| 队列任务代码 | `dev.sh restart worker` —— **rq worker 无热重载** |
| 新增 alembic 迁移 | `dev.sh restart python`（启动时跑迁移） |

**worker 最易踩**：改了上传处理逻辑后不重启，走的仍是旧代码，且不报错，
只是行为不对。

**Go 编译错误时**页面仍可用但改动未生效，先看 `make logs S=goserver`。

### 待用户决定的事项

- **Docker 数据卷 3.589GB 未清理**。这是迁移前唯一备份，`make clean-docker`
  会打印命令但不执行。建议本地环境稳定运行一两周后再执行 `docker volume prune -f`。
- **WSL `ext4.vhdx` 不会自动缩小**。Docker 内部已回收，但 Windows 侧占用不变，
  需 `wsl --shutdown` 后 `Optimize-VHD -Mode Full`。

## 遗留事项

- **`tests/08_news/NewsFeed.test.tsx` 一个用例失败**。在干净 `HEAD` 上同样失败，
  与本地化无关，属独立议题。
- **`papers.knowledge_graph_title` 列与 alembic 状态曾不一致**。列已存在但
  revision 未记录，Docker 库中亦然，说明是手工加的列。已 `stamp head` 对齐，
  但同类手工改库的做法值得约束。
- **`python.Dockerfile` 的 336MB 无效 purge 未修**。本地化后该文件只用于生产，
  多阶段构建改造属独立议题。
- **`scripts/migrate-from-docker.sh` 仍依赖 Docker**（需 alpine 容器读卷）。
  这是一次性脚本，卷清理后即可连同删除。
- **`docker/nginx.conf` 的上传相关配置未在本地链路复现**。本地走 vite 代理，
  没有 nginx 的 `client_max_body_size` 与 `proxy_request_buffering off`，
  大文件上传行为可能与生产不同，待核验。
