# 实施计划：统一「研究驱动力」字段

**GitHub Issue**：[#66](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/66)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

一次跨四层的字段改名 + 语义变更：数据库列、Python 模型与解析链路、Go 模型与 API、
前端三个界面。核心难点不是单点改动，而是**任一层漏改都会导致读写不对称**且不易发现。

## 技术上下文

- **语言与版本**：Python 3.12（SQLAlchemy、Alembic）、Go 1.25（GORM）、
  TypeScript 5.6 + React 19
- **数据存储**：MySQL（`papers` 表）、Neo4j（论文节点属性）
- **测试体系**：`pytest backend/tests`、容器内 `go test ./...`、`vitest run`
- **约束**：
  - 删列不可逆，须先确认存量数据处置
  - 三个语言层的字段名必须一致，否则读写不对称
  - 不得触碰 `backend/rag/inspiration/` 下的同名 `rationale`

## 受影响位置清单（已逐一核实）

### 数据库
- `backend/models.py:367` — `rationale = Column(Text)`
- 新增迁移：加 `research_motivation`、删 `rationale`

### Python 解析链路
- `backend/ingest/upload_jobs.py:126` — `SUMMARY_SYSTEM_PROMPT` 返回结构
- `backend/ingest/upload_jobs.py:1098` — `rationale` 与 `classification_reason` 互相兜底
- `backend/ingest/upload_jobs.py:1141` — 反向兜底
- `backend/ingest/upload_jobs.py:157、579` — 草稿模板的 `classification_reason`
- `backend/api/rag.py:1046` — 落库时两个名字兜底
- `backend/ingest/enrich_papers.py:70、84` — 离线富化脚本的字段与提示词
- `backend/ingest/sync_neo4j.py:29、54` — `PAPER_FIELDS` 与 SELECT 语句

### Go
- `goserver/models/models.go:116` — `Rationale *string`
- `goserver/handlers/papers.go:159` — 白名单 PATCH
- `goserver/handlers/papers.go:488` — 详情响应
- `goserver/handlers/admin.go:37` — 管理员可更新字段

### 前端
- `frontend/src/lib/paperProcessing.ts:154、221` — 类型定义与草稿初值
- `frontend/src/lib/paperProcessing.ts:164、226` — `classification_reason` 同上
- `frontend/src/pages/AdminPage.tsx:1060-1061` — 编辑页标签与绑定
- `frontend/src/pages/AdminPage.tsx:302-303` — 审核快照的 `classification_reason`
- `frontend/src/components/PaperEditView.tsx:46、63、378-379` — 详情页只读展示
- `frontend/src/components/UploadTaskEditor.tsx:965-968` — 校对页输入框与证据提示

### 测试
- `tests/01_decentralized_uploading/paper-detail-form-parity.test.tsx:195` — 夹具字段名

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | Alembic 迁移 `0066`：add + drop | `SHOW COLUMNS` 断言 |
| FR-002 | 三处界面标签替换 | 界面核对 + grep 断言无旧标签 |
| FR-003 | 草稿层统一字段名，删除兜底分支 | pytest 覆盖草稿落库 |
| FR-004 | `SUMMARY_SYSTEM_PROMPT` 增加字段说明 | 真实上传后核对产出 |
| FR-005 | 校对页与编辑页保持可编辑 | vitest 断言输入框可改 |
| FR-006 | `sync_neo4j.py` 两处替换 | 执行同步脚本 |
| FR-007 | Go 四处替换 | `go test` + PATCH 端到端 |
| FR-008 | 移除 `classification_context.classification_reason` | vitest 断言请求体 |
| FR-009 | 详情页保留 `pre-wrap` | vitest 断言 computed style |

## 实施顺序

顺序有依赖：**先改代码再删列**，否则删列后旧代码立刻报缺列错误。

1. **Python 层**：模型、解析链路、提示词、Neo4j 同步
2. **Go 层**：模型、白名单、响应、管理员字段
3. **前端层**：类型定义、三个界面、审核快照
4. **测试夹具**：更新字段名
5. **迁移**：新增 `research_motivation` + 删除 `rationale`
6. **重建镜像**：python 与 goserver（改了迁移必须重建 python 镜像）
7. **验证**：编译、单测、真实上传、Neo4j 同步

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 删列不可逆 | 存量仅 1 行且为旧语义，已确认不迁移；迁移 `downgrade()` 可重建空列 |
| 某层漏改导致读写不对称 | 以「受影响位置清单」逐项核对，改完用 grep 全仓库确认无残留 |
| 误改灵感探索模块的同名字段 | 所有 grep 排除 `rag/inspiration/`、`rag/core/engine`、`rag/agent/graph` |
| 提示词改动后 LLM 产出不合要求 | 真实上传一篇 PDF 核对字数、分条与来源 |
| 迁移文件未进镜像导致整栈起不来 | 改迁移后必须 `build python`，不能只用挂载容器升级库 |
