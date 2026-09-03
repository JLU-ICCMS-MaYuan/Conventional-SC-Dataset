# 功能规格：恢复引用图谱运行链路并回填历史引用

**GitHub Issue**：[ #82](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/82)

**关联 Feature**：[ #81](../81-citation-graph/spec.md)

**创建日期**：2026-09-03

**状态**：已确认

## 问题事实

2026-09-03 的本地运行诊断确认：

- 浏览器访问 `http://127.0.0.1:5173/api/knowledge-graph/overview` 超时。
- Vite 将全部 `/api` 请求代理到 Go `:8080`；Python `:8000` 不是公开 API 的直接入口。
- Go 服务在路由注册阶段 panic：`/api/admin/papers/:id` 与
  `/api/admin/papers/:paperId/graph-marks` 的同位置通配参数名称不一致。
- 运行诊断开始时，开发库 `scwiki` 停在 `paper_superconductor_kind`，没有应用 #81 的
  `paper_citation_graph` Alembic 迁移；本 Issue 的受控上线已将其迁移至目标版本。
- 历史论文只有 `paper_files`，没有 `paper_references`。#81 的上传、升版和审核
  流程会解析新版本，却没有可显式执行的历史回填入口。
- 运行诊断开始时，本地开发环境没有 GROBID 服务管理或 `GROBID_URL`。Compose 内的
  `grobid` 主机名无法被宿主机 Python/Worker 使用。

因此，代码测试通过不等于开发环境已可用。本 Issue 负责修复运行故障、应用已验证
的 schema，并为已收录论文建立可控的首次引用解析能力。

## 目标

1. 恢复 Go `:8080` 服务，使 Vite 经由 Go 的公开 API 链路不再超时。
2. 将开发库 `scwiki` 安全升级至 `paper_citation_graph`。
3. 提供历史已审核论文的显式、幂等 GROBID 回填命令。
4. 不改变 #81 已确定的引用事实、分类、权限或图遍历语义。

## 用户场景与验收

### 用户故事 1：站点 API 能正常启动（P1）

作为读者，我打开任意需要 `/api` 的页面时，页面不应因 Go 路由注册失败而一直加载。

**验收场景**：

1. **假如**Go 服务启动，**当**注册管理员论文更新和图谱里程碑路由，**那么**进程
   不 panic，`GET /health` 返回 200。
2. **假如**Vite 正在运行，**当**请求 `/api/knowledge-graph/overview`，**那么**请求
   到达 Go 服务；未迁移前可以返回明确的后端错误，但不得连接超时。

### 用户故事 2：开发库具备引用图谱 schema（P1）

作为管理员，我需要将已经测试过的引用表迁移应用到实际开发库，以使服务有可查询的
表结构。

**验收场景**：

1. **假如**`scwiki.papers.year` 没有空值，**当**运行迁移，**那么**Alembic 版本到达
   `paper_citation_graph`，并创建 `paper_reference_extractions`、`paper_references`
   和 `paper_graph_marks`。
2. **假如**迁移前发现空年份，**当**运行迁移，**那么**迁移明确失败，不猜测或写入
   年份。

### 用户故事 3：历史论文可以回填引用（P1）

作为管理员，我需要让 #81 实现前已审核的主 PDF 也通过 GROBID 生成可追溯的参考
文献记录，而不用伪造边或修改论文版本。

**验收场景**：

1. **假如**一篇论文是当前已审核版本且有 `role = main` 的本地 PDF，**当**运行指定
   论文 ID 的回填命令，**那么**调用 GROBID，并将结果写入该 `paper_id` 与当前
   `content_revision`。
2. **假如**同一论文被重复回填，**当**PDF 和版本未变，**那么**仅替换本版本的
   `paper_references` 与提取状态，不产生重复记录或论文新 revision。
3. **假如**GROBID 不可用、PDF 缺失或解析失败，**当**命令继续处理其他论文，**那么**
   对该论文记录可观察的失败状态或跳过原因，不创建人工/LLM 引用边。
4. **假如**目标论文之后审核通过，**当**现有 `reconcile_after_paper_approval` 执行，
   **那么**历史未匹配引文按 #81 的 DOI 优先、唯一题名规则重新匹配。

## 功能需求

- **FR-001**：管理员里程碑 URL 必须保持
  `PUT /api/admin/papers/{paperId}/graph-marks`；Go 路由内部必须与同组
  `/papers/:id` 使用同名 `:id` 参数，handler 读取 `id`。
- **FR-002**：测试必须覆盖这两条管理员论文路由在同一 Gin router 注册时不 panic。
  单个 handler 的 mock router 不可作为该启动安全性的唯一测试。
- **FR-003**：开发库迁移前必须读取实际 Alembic 版本、空年份计数和目标表存在性；
  迁移后必须再次验证版本、表和 Vite 到 Go 的 HTTP 链路。
- **FR-004**：新增仅供运维人员在本地执行的 Python CLI，不提供公开 HTTP 回填端点。
  命令必须要求 `--paper-id`（可重复）或显式 `--all-approved`，没有目标时拒绝执行。
- **FR-005**：回填范围只能是 `review_status = approved`、
  `approved_revision = content_revision`、且具有当前 revision 主 PDF 的论文。
  `--all-approved` 必须按稳定 `paper_id` 顺序处理。
- **FR-006**：每篇论文的 GROBID 调用必须在数据库写事务之外；获得结果后在独立事务
  中调用既有 `persist_reference_extraction`。单篇失败不得回滚其他论文的成功结果。
- **FR-007**：回填不得改变 `papers.content_revision`、审核状态、分类、主文件或
  `knowledge_graph_title`。匹配规则只能复用 #81 的 `citation_graph.py`。
- **FR-008**：命令必须输出每篇论文的 ID、版本、结果状态、参考文献数量及失败/跳过
  原因；进程退出码在有失败论文时为非零，便于运维发现不完整回填。
- **FR-009**：本地开发必须通过 `scripts/dev.sh` 管理名为 `grobid` 的
  `lfoppiano/grobid:0.8.1` 容器；容器只能发布 `127.0.0.1:8070`，并等待
  `/api/isalive` 成功后才报告启动完成。当前 WSL cgroup 环境中必须传入
  `JAVA_TOOL_OPTIONS=-XX:-UseContainerSupport`，避免 Java 在启动阶段崩溃。
- **FR-010**：本地 `.env` 必须将 `GROBID_URL` 指向 `http://127.0.0.1:8070`；
  Python 和 Worker 重启后才可使用新环境变量。该配置不得写入版本库或生产密钥文档。

## 范围外事项

- 不将外部参考文献或 Neo4j 自由文本创建为 SC-Wiki 图节点。
- 不自动批准论文、改变材料分类，或根据被引次数自动标记源头/突破。
- 不在浏览器端提供批量回填按钮；这是一项受控运维操作。
- 不承诺 GROBID 对任何 PDF 都能解析成功。

## 数据与安全约束

- `scwiki` 是实际开发库；`scwiki_test` 只用于可清空的测试 fixture。二者不得混用。
- 数据库迁移和实际回填均须由明确授权执行；本 Issue 的授权已获得。
- MySQL 是引用事实唯一来源。回填只保存 GROBID 原始引文及其保守匹配结果。
- 当前库只有一篇已审核论文。即使回填成功，若没有第二篇已收录论文匹配其参考文献，
  图谱也应正确显示一个孤立节点，而非虚构关系。

## 成功标准

- **SC-001**：`go test ./...` 通过，且完整路由注册的回归测试可捕获此前的 Gin 冲突。
- **SC-002**：Go 服务可在 `:8080` 启动，`GET /health` 返回 200；Vite 代理图谱
  概览请求不再超时。
- **SC-003**：`scwiki` 迁移版本为 `paper_citation_graph`，目标引用表均存在。
- **SC-004**：指定历史论文的回填命令可重跑，不改论文 revision，不重复引用记录。
- **SC-005**：GROBID 不可用时，命令不伪造引用边，并以非零退出码报告失败。
- **SC-006**：`scripts/dev.sh start grobid`、`status`、`stop grobid` 可管理本地
  GROBID；健康检查通过后，指定历史 PDF 的实际回填能保存提取状态。

## 实际验收记录

### 2026-09-03

- 开发库已迁移到 `paper_citation_graph`，目标引用表均已创建。
- 本地 GROBID 使用 `lfoppiano/grobid:0.8.1`，仅监听 `127.0.0.1:8070`；健康接口
  返回 200。
- Python、Worker、Go 和 Vite 均已运行。浏览器同路径的图谱概览返回 200。
- 论文 `9` 的当前已审核版本 `3` 已连续回填两次；每次均为 `partial`、解析 1 条原始
  引文。数据库最终保留 1 条提取记录和 1 条未匹配引文，没有产生重复记录或新 revision。
- 图谱只有论文 `9` 一个节点且没有边是正确结果：当前库没有第二篇已审核论文可被该引文
  匹配。
