# 实施任务：统一「研究驱动力」字段

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**顺序约束**：先改全部代码，最后执行迁移（见 research.md 决策6）。

## 阶段 1：Python 数据层与解析链路

- [ ] T001 `backend/models.py:367` 将 `rationale` 改为 `research_motivation`
- [ ] T002 `backend/ingest/upload_jobs.py:126` `SUMMARY_SYSTEM_PROMPT` 返回结构中
  `"rationale": ""` 改为 `"research_motivation": ""`
- [ ] T003 [US3] `SUMMARY_SYSTEM_PROMPT` 正文新增字段说明：内容为作者开展该研究的动因，
  依据引言与背景段落、不得编造、信息不足留空，≤500 字，按 `1. 2. 3.` 分条
  （现有实现对该字段无任何说明，是产出偏离的根因）
- [ ] T004 `backend/ingest/upload_jobs.py:1098` 删除 `rationale`/`classification_reason`
  互相兜底，改为直接取 `research_motivation`
- [ ] T005 `backend/ingest/upload_jobs.py:1141` 同上，反向兜底一并删除
- [ ] T006 `backend/ingest/upload_jobs.py:157、579` 草稿模板的 `classification_reason`
  改为 `research_motivation`
- [ ] T007 `backend/api/rag.py:1046` 落库改为 `research_motivation=draft.get("research_motivation")`
- [ ] T008 `backend/ingest/enrich_papers.py:70、84` 离线富化脚本的字段名与提示词同步更新
  （不更新会导致两条链路字段名不一致）
- [ ] T009 `backend/ingest/sync_neo4j.py:29、54` `PAPER_FIELDS` 与 SELECT 语句替换字段名

## 阶段 2：Go 层

- [ ] T010 `goserver/models/models.go:116` `Rationale *string` 改为
  `ResearchMotivation *string`，json tag 同步
- [ ] T011 `goserver/handlers/papers.go:159` 白名单 PATCH 字段替换
- [ ] T012 `goserver/handlers/papers.go:488` 详情响应字段替换
- [ ] T013 `goserver/handlers/admin.go:37` 管理员可更新字段列表替换

## 阶段 3：前端

- [ ] T014 `frontend/src/lib/paperProcessing.ts:154、221` 类型定义与草稿初值替换
- [ ] T015 `frontend/src/lib/paperProcessing.ts:164、226` 删除 `classification_reason`
- [ ] T016 [US2] `frontend/src/pages/AdminPage.tsx:1060-1061` 标签改「研究驱动力」，
  绑定字段替换
- [ ] T017 [US2] `frontend/src/components/PaperEditView.tsx:46、63、378-379` 变量改名、
  标签改「研究驱动力」，保留 `pre-wrap`（FR-009）
- [ ] T018 [US1] `frontend/src/components/UploadTaskEditor.tsx:965-968` 标签改
  「研究驱动力」，字段与证据提示替换
- [ ] T019 `frontend/src/pages/AdminPage.tsx:302-303` 从审核请求的
  `classification_context` 移除 `classification_reason` 键（FR-008）

## 阶段 4：测试

- [ ] T020 `tests/01_decentralized_uploading/paper-detail-form-parity.test.tsx:195`
  夹具字段名替换
- [ ] T021 新增前端测试：三个界面显示「研究驱动力」，且不存在「分类理由」「研究理由」
- [ ] T022 新增前端测试：审核请求体的 `classification_context` 不含
  `classification_reason` 键
- [ ] T023 全仓库 grep 确认论文侧 `rationale` 与 `classification_reason` 已清除
  （排除 `rag/inspiration/`、`rag/core/engine`、`rag/agent/graph`）

## 阶段 5：迁移与部署

**必须在阶段 1–4 全部完成后执行**，否则代码与库结构不匹配。

- [ ] T024 新建 `alembic/versions/20260831_0066_research_motivation.py`：
  add `research_motivation`（Text，可空）+ drop `rationale`；`downgrade()` 反向
- [ ] T025 `docker compose build python goserver`
  （改迁移必须重建 python 镜像，否则库版本领先镜像导致整栈起不来）
- [ ] T026 执行 `alembic upgrade head`
- [ ] T027 `docker compose up -d python goserver worker` 并 `restart frontend`
  （nginx 缓存旧容器 IP 会导致全站 502）

## 阶段 6：验证

- [ ] T028 `SHOW COLUMNS` 确认有 `research_motivation`、无 `rationale`（SC-001）
- [ ] T029 容器内 `go build ./...` 与 `go test ./...` 通过
- [ ] T030 `npx tsc -b --force` 与 `npx vitest run` 通过
- [ ] T031 `pytest backend/tests` 通过
- [ ] T032 [US3] 真实上传一篇含引言的 PDF，核对 `research_motivation` 满足
  ≤500 字、`1. 2. 3.` 分条、来源为引言（SC-004）
- [ ] T033 执行 Neo4j 同步脚本，确认不报缺列错误（SC-005）
- [ ] T034 端到端 PATCH：`research_motivation` 被接受、`rationale` 被拒绝（SC-006）
- [ ] T035 界面核对三处标签（SC-002）

## 阶段 7：文档

- [ ] T036 更新 `docs/overview/02_.../mysql-schema-catalog.md:130` 富化内容字段列表
- [ ] T037 更新 `docs/overview/01_.../pdf-ingestion.md:49`：Issue #59 的「分类理由」
  表述已被本 Feature 取代，需说明语义演进而非简单覆盖
- [ ] T038 更新 `docs/overview/03_.../paper-and-property-results.md:17`：
  `pre-wrap` 字段清单中的 `rationale` 改名
- [ ] T039 在 Issue #66 回写实现总结与验收结果

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001 | T001、T024 | SHOW COLUMNS |
| FR-002 | T016–T018、T021 | 界面核对 + 测试断言 |
| FR-003 | T004–T007、T015 | pytest 草稿落库 |
| FR-004 | T003 | 真实上传核对产出 |
| FR-005 | T016、T018 | 输入框可编辑 |
| FR-006 | T009、T033 | 同步脚本执行 |
| FR-007 | T010–T013、T034 | go test + PATCH |
| FR-008 | T019、T022 | 请求体断言 |
| FR-009 | T017 | pre-wrap 保留 |

## 依赖与执行顺序

- 阶段 1–3 可并行（不同语言层），但**必须全部完成后**才执行阶段 5
- 阶段 4 依赖 1–3
- 阶段 6 依赖 5
- Issue #67（联网增强）依赖本 Feature 的 T003 提示词落地
