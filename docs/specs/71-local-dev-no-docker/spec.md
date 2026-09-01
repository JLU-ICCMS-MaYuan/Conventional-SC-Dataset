# Feature 规格：本地化开发环境，移除 Docker 依赖

**GitHub Issue**：[#71](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/71)

**创建日期**：2026-09-01

**状态**：已落地

## 背景与目标

Docker 镜像层不可变，重建从来不是「在旧镜像上覆盖」—— 每次 build 产出全新的层，
旧层原地留着，只是 `latest` 标签挪到新镜像上，旧镜像随即变成 dangling 并继续占磁盘。

会话开始时的实测占用：

```
Images          16  ACTIVE 10   19.8GB   可回收 17.43GB (88%)
Containers      24  ACTIVE 10   822MB    可回收 541MB
Build Cache     92              8.62GB   可回收 6GB
```

根分区当时 222G/251G（93%），仅剩 17G。

垃圾全部来自三个从源码构建的服务。官方镜像（MySQL/Redis/Neo4j/Qdrant）直接拉取，
从不参与 build，不产生任何垃圾：

| 服务 | 来源 | 每次重建产生 |
|---|---|---|
| python / worker / migrate / news-* | `docker/python.Dockerfile` | 1.89GB，改 requirements 即整层重造 |
| goserver | `docker/goserver.Dockerfile` | 54MB + Go 构建缓存 |
| frontend | `docker/frontend.Dockerfile` | 96MB，且须先跑 `vite build` 才能看到改动 |

`python.Dockerfile` 另有一处无效优化：`apt-get purge build-essential` 与 `pip install`
写在同一 `RUN`，但编译器是**上一层**装的。上层删下层文件只写 whiteout 标记，
那 336MB 仍完整留在镜像里，且每次 base 层失效时会再来一份。

**业务价值**：
- 反馈速度：前端改动原本需 `vite build` + 重建镜像，本地化后 HMR 即时生效
- 磁盘可控：不再有「越用越涨」的镜像与构建缓存
- 测试便利：后端 pytest 原本必须用挂载仓库的一次性容器，本地化后直接跑

## 用户场景与验收

### 用户故事 1：开发者改代码后立即看到效果（优先级：P1）

开发者修改前端组件、Python 接口或 Go 处理器后，希望刷新页面即可验证，
不需要重建镜像或重启容器。

**独立验收**：三类代码各改一行，均能在数秒内生效。

**验收场景**：

1. **假如** 开发者修改 `frontend/src/**`，**当** 保存文件，**那么** 浏览器通过 HMR
   自动更新，无需手动刷新
2. **假如** 开发者修改 `backend/**`，**当** 保存文件，**那么** uvicorn 在 1-2 秒内重启，
   日志出现 `WatchFiles detected changes`
3. **假如** 开发者修改 `goserver/**/*.go`，**当** 保存文件，**那么** 约 1 秒内重新编译
   并重启，进程 pid 改变
4. **假如** Go 代码有编译错误，**当** 保存文件，**那么** 保留旧进程继续服务，
   仅在日志报错，不造成服务中断

### 用户故事 2：开发者一条命令启停整套环境（优先级：P1）

开发者希望不必记住 8 个服务的启动参数与依赖顺序。

**独立验收**：`make start` 启动全部，`make stop` 全部干净退出无残留。

**验收场景**：

1. **假如** 环境已安装，**当** 执行 `make start`，**那么** 8 个服务按依赖顺序启动，
   每个都等到健康检查通过才继续
2. **假如** 服务已在运行，**当** 再次 `make start`，**那么** 跳过并提示「已在运行」（幂等）
3. **假如** 执行 `make stop`，**那么** 全部服务退出，端口释放，无残留进程
4. **假如** 某端口被占用，**当** 启动该服务，**那么** 明确报错而非静默失败

### 用户故事 3：开发者迁移既有数据且可回退（优先级：P1）

开发者需要把 Docker 卷中的数据搬到本地，且迁移出错时能回到原状态。

**独立验收**：迁移后行数与 Docker 侧逐项一致；原卷完整保留。

**验收场景**：

1. **假如** 执行迁移，**那么** MySQL 表数与行数、Neo4j 节点数、Qdrant 点数
   与 Docker 侧一致
2. **假如** 迁移过程中任一步失败，**那么** 原 Docker 卷未被修改或删除
3. **假如** 目标目录已有数据，**当** 重复执行迁移，**那么** 跳过而非覆盖

### 边界与异常场景

- **端口冲突**：宿主机 3306 已被系统级 MySQL 8.0（`/usr/sbin/mysqld`）占用，
  与本项目无关。本项目 MySQL 用 3307。
- **MySQL 版本降级**：Docker 端 8.4.11 → conda-forge 最高 8.4.2。MySQL 拒绝打开
  高版本 datadir，物理拷贝必定失败，必须逻辑导出。
- **Redis AOF 损坏**：Docker 卷中 `appendonly.aof.3.incr.aof` 已损坏（daemon 异常
  重启所致）。Redis 只存队列与缓存，非权威数据，迁移只取 RDB。
- **Neo4j 官方源不可达**：全部返回 403，见「假设与依赖」。
- **worker 无热重载**：rq worker 加载启动那刻的代码，改队列任务须手动重启。

## 需求

### 功能需求

- **FR-001** 四个基础服务（MySQL/Redis/Neo4j/Qdrant）必须运行在宿主机，不使用容器
- **FR-002** 三个应用服务（python/goserver/frontend）必须支持代码热重载
- **FR-003** 全部数据必须存放于仓库内 `.data/`，且已 gitignore
- **FR-004** Python 依赖必须使用既有 conda 环境 `sc-wiki`
- **FR-005** 启停必须由单一命令驱动，且幂等
- **FR-006** 启动必须等待健康检查通过，不得在依赖未就绪时继续
- **FR-007** 数据迁移必须保持原 Docker 卷只读，不删除不修改
- **FR-008** 迁移必须按各服务版本差异选择物理拷贝或逻辑导出
- **FR-009** 所有 mysql 客户端命令必须 `--defaults-file` 隔离，避免读到系统配置
- **FR-010** Go 编译失败时必须保留旧进程继续服务
- **FR-011** 测试必须能在宿主机直接运行，不依赖容器
- **FR-012** 破坏性清理命令只打印不执行，由用户确认后手动运行

### 不做的需求

- 不修改任何 `backend/` 或 `goserver/` 源码。所有连接地址本来就走环境变量
- 不删除 `docker/` 下的 Dockerfile 与 compose 文件，它们是生产部署产物
- 不默认启动 `news-worker` / `news-scheduler`，日常开发用不上（YAGNI）
- 不自动执行 Docker 清理，尤其不自动删除数据卷

### 关键实体

- **`.data/`** — 全部持久数据：四个数据库的数据目录、上传文件、解析产物、头像
- **`.local/`** — 运行时：Neo4j 与 Qdrant 二进制、MySQL 配置、pid、日志、goserver 产物
- **`sc-wiki`** — conda 环境，应用 Python 依赖
- **`sc-wiki-infra`** — conda 环境，mysqld / redis-server / openjdk 21 / mysql 客户端

## 成功标准

- **SC-001** 四个基础服务本地启动并通过健康检查 —— ✅ MySQL 8.4.2 / Redis 8.10.1 /
  Neo4j 5.26.29 / Qdrant 1.19.0
- **SC-002** 数据迁移行数与 Docker 侧一致 —— ✅ 35 张表；`periodic_table_elements` 118、
  `news_feed_identities` 87、`news_feed_items` 72、`papers` 1、`superconductors` 9、
  `users` 3；Neo4j 517MB、Qdrant 369MB
- **SC-003** 全链路可用 —— ✅ 浏览器 → vite:5173 → goserver:8080 → uvicorn:8000，
  知识图谱与检索均返回正确数据
- **SC-004** Go 热重载生效 —— ✅ 改 `main.go` 后 pid 由 1546962 变为 1552510
- **SC-005** Python 热重载生效 —— ✅ 日志出现 `WatchFiles detected changes in 'backend/main.py'`
- **SC-006** 后端测试通过 —— ✅ pytest 116 passed
- **SC-007** goserver 测试通过 —— ✅ 全部 package ok
- **SC-008** 前端测试无新增失败 —— ✅ 109/110；唯一失败在干净 `HEAD` 上同样失败
- **SC-009** 全量停止无残留 —— ✅ 10 个服务干净退出，端口与进程均无残留
- **SC-010** Docker 资源清零 —— ✅ Images/Containers/Build Cache 均 0B

## 假设与依赖

- **Neo4j 必须从镜像提取**：`dist.neo4j.org`、`debian.neo4j.com`，以及 aliyun /
  tuna / ustc / 腾讯 / 华为镜像全部返回 403（CDN 地域封锁，带完整浏览器头亦然）。
  `neo4j:5` 镜像内是纯 Java 应用，提取后可独立运行。这是一次性动作，提取完镜像即可删除。
- **Qdrant 经 GitHub 加速镜像下载**：GitHub 直连不可达，`gh-proxy.com` 可用
  （`ghproxy.net`、`hub.gitmirror.com` 均不可用）。选 musl 静态版，无动态库依赖。
- **两个 conda 环境必须分开**：把 `mysql-server` 装进 `sc-wiki` 会迫使 conda 将
  `python` 从 `pkgs/main` 换成 `conda-forge` 版本（dry-run 实测），危及已有的 161 个包。
- **`sudo` 需要密码**：故所有安装走 conda 与用户目录，不用 apt。
- **卷内文件属主非当前用户**（999:999 / 7474:7474），宿主机 chown 需 root，
  故迁移在一次性 alpine 容器内完成 `cp -a` + `chown`。

## 范围外事项

- 生产部署方式不变，仍用 `docker/` 下的 compose 与 Dockerfile
- 不优化 `python.Dockerfile` 的多阶段构建。本地化后它只用于生产，
  那 336MB 无效 purge 属独立议题
- 不清理 Docker 数据卷。它是迁移前唯一备份，留待用户确认后自行处理
- WSL `ext4.vhdx` 不会因 Docker 清理自动缩小，需 Windows 侧 `Optimize-VHD`，
  属宿主机运维，不在本次范围

## 澄清记录

### 2026-09-01

- **Q**：`.data` 存放范围是仅应用数据还是含数据库？
  **A**：全部放 `.data`，含 MySQL/Neo4j/Qdrant/Redis 的数据文件。
- **Q**：四个基础服务保留 Docker 长驻还是装到本机？
  **A**：先选保留 Docker 长驻；用户随后明确要求彻底移除 Docker，改为全部本地安装。
- **Q**：GitHub 上 Issue #71 不存在（最大 #69），spec 目录编号如何处理？
  **A**：新建 Issue 并关闭。新建后发现 #70 与已提交的 `70-knowledge-graph-title`
  冲突（那份 spec 引用的 #70 当时并未实际创建），故将 #70 改写为知识图谱标题，
  本 spec 另建 #71。
