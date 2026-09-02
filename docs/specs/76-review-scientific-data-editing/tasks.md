# 实施任务：审核编辑页补齐超导性质并支持完全编辑

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认依赖就位、记录测试基线、准备验证数据。

- [ ] T001 确认 Issue #74 的 i18n 基建已就位（`frontend/src/context/LanguageContext.tsx` 与 `frontend/src/i18n/{zh,en}/admin.ts` 存在），新增文案直接走双语字典
- [ ] T002 确认 #74 的 T019、#75 的 T014 对 `frontend/src/pages/AdminPage.tsx` 的改动已完成，避免同文件冲突（[plan.md](plan.md) 串行触点）
- [ ] T003 执行 `scripts/run-tests.sh frontend`、`go`、`backend` 与 `python -m pytest tests -q` 记录基线，确认 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例不计入本 Feature 回归
- [ ] T004 准备验证数据：确认存在一篇 `pending` 与一篇 `approved` 论文（如 `papers.id = 9`），各含 2 个以上材料状态且其下有 Tc 与普通物性；记录 `paper_files`/`paper_chunks`/`paper_evidences`/`material_states` 的行数备升版比对

## 阶段 2：基础能力——外键级联链迁移

**目的**：建立单向级联链，使升版可执行。这是 US4 的硬前提；缺它则任何 `papers.content_revision` 更新都被 RESTRICT 外键拒绝。

### 测试

- [ ] T005 [P] 在 `tests/02_maintenance_and_verification/test_revision_cascade_chain.py` 新增真实 MySQL 集成测试：迁移后单条 `UPDATE papers SET content_revision=N+1, approved_revision=NULL, review_status='pending'` 使 `paper_files`、`paper_chunks`、`paper_evidences`、`material_states` 的 `paper_revision` 全部变为 N+1，且各表行数不变（[data-model.md](data-model.md) 外键迁移、R3）
- [ ] T006 [P] 在同一文件新增测试：事务内升版后抛异常回滚，主表与全部子表的版本号一同回到原值，无中间态残留（FR-018、R3）
- [ ] T007 [P] 在同一文件新增测试：删除两条直连外键后完整性不放松——无法插入 `paper_id` 不存在的 chunk、无法删除仍被引用的 paper、无法删除仍被 chunk 引用的 file（[data-model.md](data-model.md) 完整性验证）
- [ ] T008 [P] 在同一文件新增测试：`ON DELETE RESTRICT` 未被改动，`paper_deletion.go` 的既有删除链路行为不变

### 实施

- [ ] T009 新增 `alembic/versions/<rev>_revision_cascade_chain.py`：把 `fk_paper_files_paper_revision`、`fk_paper_chunks_file_revision`、`fk_paper_evidences_chunk_revision`、`fk_material_states_paper_revision` 四条外键改为 `ON UPDATE CASCADE`（`ON DELETE` 保持 RESTRICT），删除 `fk_paper_chunks_paper_revision` 与 `fk_paper_evidences_paper_revision` 两条冗余直连（[data-model.md](data-model.md) 外键迁移、R3）
- [ ] T010 在同一迁移文件实现 `downgrade`：4 条外键改回 `ON UPDATE NO ACTION`、重建 2 条直连；检测到 `content_revision > 1` 的论文时报错而非静默执行（[data-model.md](data-model.md) 迁移可逆性）
- [ ] T011 应用迁移并用 `information_schema.REFERENTIAL_CONSTRAINTS` 核对 6 条外键的 `UPDATE_RULE` 与 `DELETE_RULE` 符合目标结构；注意多 CASCADE 冲突在建表期不报错，必须靠 T005 的运行时测试确认

## 阶段 3：基础能力——数据可见性

**目的**：补齐详情接口缺失的预加载。这是 FR-002–FR-004 的前提，缺它则编辑页拿不到 Tc、物性与结构。

### 测试

- [ ] T012 [P] 在 `goserver/handlers/paper_detail_test.go` 新增测试：`GET /api/admin/papers/:id` 响应的 `material_states[]` 含非空 `tc_results`、`properties`、`structures`（契约 [scientific-draft-api.md](contracts/scientific-draft-api.md) C3）

### 实施

- [ ] T013 修改 `goserver/handlers/admin.go` 的 `GetPaperDetail`（124–128 行）：补 `Preload("MaterialStates.TcResults")`、`Preload("MaterialStates.Properties")`、`Preload("MaterialStates.Structures")`（FR-002、FR-003、FR-004、C3）

## 阶段 4：基础能力——共享组件抽取

**目的**：把材料状态编辑区抽成共享受控组件。纯重构，不新增功能，必须先绿再进入功能开发（US5，P1 底线）。

- [ ] T014 新增 `frontend/src/components/MaterialStatesEditor.tsx`：从 `frontend/src/components/UploadTaskEditor.tsx` 1020–1284 行抽出材料状态编辑区，props 为 `states / onChange / catalogs / readOnly / issues`（[research.md](research.md) R5、FR-023）
- [ ] T015 修改 `frontend/src/components/UploadTaskEditor.tsx`：改为消费 `MaterialStatesEditor`，删除已抽出的内联实现，保持对外行为不变（FR-022）
- [ ] T016 执行 `scripts/run-tests.sh frontend`，确认 `tests/01_decentralized_uploading/` 下 upload-task-editor-classification、upload-task-editor-layout、submit-validation-feedback 等既有用例全部通过（FR-022、SC-008）
- [ ] T017 [P] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 新增测试：共享组件在 `readOnly` 下不可编辑、`issues` 传入时字段显示错误态、`onChange` 回调传出完整状态数组（FR-023）

## 阶段 5：用户故事 1——管理员查看完整超导性质（P1，MVP）

**目标**：审核者一次看清全部科学数据再决定通过或退回。

**独立验收**：编辑弹窗呈现全部材料状态卡片及其下的 Tc、物性、结构附件。

### 测试

- [ ] T018 [P] [US1] 在 `tests/02_identity_governance/admin-scientific-data-view.test.tsx` 新增测试：编辑弹窗渲染全部材料状态及其八项字段（FR-001、SC-001）
- [ ] T019 [P] [US1] 在 `tests/02_identity_governance/admin-scientific-data-view.test.tsx` 新增测试：Tc 列表、普通物性列表、结构预览均可见；无材料状态时显示空态不报错（FR-002–FR-004、US1 场景 5）

### 实施

- [ ] T020 [US1] 修改 `frontend/src/pages/AdminPage.tsx`：编辑弹窗集成 `MaterialStatesEditor`，先以 `readOnly` 模式展示，验证数据链路通畅（FR-001–FR-004）
- [ ] T021 [P] [US1] 修改 `frontend/src/i18n/zh/admin.ts` 与 `frontend/src/i18n/en/admin.ts`：新增材料状态编辑区相关文案条目

## 阶段 6：用户故事 2——待审核论文原地编辑（P1）

**目标**：管理员当场修正待审核论文的科学数据，不必退回上传者。

**独立验收**：修改待审核论文的科学数据保存后生效，且论文版本号不变。

### 测试

- [ ] T022 [P] [US2] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：`pending` 论文保存后 `content_revision` 不变、`approved_revision` 为 NULL、`review_status` 仍为 `pending`（FR-012、SC-002）
- [ ] T023 [P] [US2] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：删除顺序正确执行，含 `structure_models` 自引用先置空；重建后数据与请求体一致（[data-model.md](data-model.md) 删除顺序、R4）
- [ ] T024 [P] [US2] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：校验规则复用生效——缺化学式、缺材料家族、压强区间 min 大于 max 均被 400 拒绝且错误含材料状态序号（FR-020、C1 错误契约）
- [ ] T025 [P] [US2] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：综述论文的 `material_states` 为空数组时保存成功（US2 场景 7）
- [ ] T026 [P] [US2] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：跨论文共享目录表（`superconductors`、`material_families`、`structure_families`、`property_definitions`）在保存前后行数不变（[data-model.md](data-model.md)）
- [ ] T027 [P] [US2] 在 `tests/02_identity_governance/admin-scientific-data-edit.test.tsx` 新增测试：增删改材料状态、Tc、普通物性的交互，保存后请求体结构符合契约 C1（FR-005、FR-006、FR-007、FR-008、FR-011）

### 实施

- [ ] T028 [US2] 新增 `backend/services/scientific_draft_rewrite.py`：单事务编排——按依赖顺序删除科学实体（6 步，含自引用置空）后调用 `persist_scientific_draft` 重建（R1、R4、FR-018）
- [ ] T029 [US2] 修改 `backend/api/rag.py`：新增 `PUT /api/rag/papers/{paper_id}/scientific-draft` 端点，`get_current_admin` 鉴权，`pending` 分支原地重建，复用 `_validate_draft` 校验（契约 C1、FR-012、FR-020、FR-021）
- [ ] T030 [US2] 修改 `frontend/src/pages/AdminPage.tsx`：`MaterialStatesEditor` 由只读改为可编辑，接入两段保存编排（论文级走 Go、科学数据走 C1），失败提示指明失败部分（FR-005、FR-006、FR-007、FR-008、FR-011、FR-019、契约 C4）

## 阶段 7：用户故事 3——审核页补传结构附件（P2）

**目标**：审核时缺结构文件可直接补传，不走退回流程。

**独立验收**：为某材料状态上传 CIF，通过校验并可预览。

### 测试

- [ ] T031 [P] [US3] 在 `backend/tests/test_paper_structure_candidates.py` 新增测试：合法 CIF 产出候选且不写入 `structure_models`；非法文件 400 且不写库；下标越界 400（FR-009、FR-010、契约 C2）
- [ ] T032 [P] [US3] 在 `tests/02_identity_governance/admin-structure-upload.test.tsx` 新增测试：上传后在对应材料状态下预览；删除结构附件后保存生效（FR-009、FR-008）

### 实施

- [ ] T033 [US3] 修改 `backend/api/rag.py`：新增 `POST /api/rag/papers/{paper_id}/structure-candidates` 端点，复用 `build_structure_candidate` 校验与表示生成（契约 C2、R6、FR-021）
- [ ] T034 [US3] 修改 `frontend/src/components/MaterialStatesEditor.tsx`：结构区支持管理端上传路径（复用 `StructureCandidatePanel`），按消费方注入的上传回调区分上传任务与论文两种宿主

## 阶段 8：用户故事 4——已批准论文升版重审（P2）

**目标**：已公开论文的错误数据可当场修正，并通过升版重审保证公开内容经过审核。

**独立验收**：修改已批准论文的科学数据后，版本号递增、状态回到待审核、论文暂时下架，重新批准后恢复公开。

### 测试

- [ ] T035 [P] [US4] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：`approved` 论文保存后 `content_revision` 递增、`approved_revision` 为 NULL、`review_status` 为 `pending`，且 `ck_papers_review_revision` 成立（FR-013、SC-003、SC-009、R7）
- [ ] T036 [P] [US4] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：升版后 `paper_files`、`paper_chunks`、`paper_evidences`、`material_states` 全部行的 `paper_revision` 为新版本号，行数与升版前相同，旧版本号下无残留（FR-014、SC-004、R3）
- [ ] T037 [P] [US4] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：升版写入 `paper_review_events` 记录（FR-016、R8）
- [ ] T038 [P] [US4] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：重建阶段失败时整体回滚——论文版本号、审核状态、科学数据与血缘数据的 `paper_revision` 全部保持原状，论文仍对外公开（FR-018、US4 场景 7、SC-006）
- [ ] T039 [P] [US4] 在 `backend/tests/test_scientific_draft_rewrite.py` 新增测试：`rejected` 论文调用端点返回 409 `paper_status_not_editable`（R10、契约 C1）
- [ ] T040 [P] [US4] 在 `goserver/handlers/paper_access_test.go` 新增测试：升版后的论文不满足公开条件，公开查询与图表接口不返回该论文；非管理员访问详情无权查看（FR-015、US4 场景 3、场景 4）
- [ ] T041 [P] [US4] 在 `tests/02_identity_governance/admin-revision-bump.test.tsx` 新增测试：已批准论文编辑页在保存前显示升版警告；保存成功后按 `revision_bumped` 提示已退回待审核（FR-017、契约 C1 响应）

### 实施

- [ ] T042 [US4] 修改 `backend/services/scientific_draft_rewrite.py`：新增升版分支——先按 6 步删除科学实体，再用**单条** UPDATE 写入三个版本字段（触发外键级联自动更新血缘数据），最后重建科学实体并写入审核事件（FR-013、FR-014、FR-016、R3、R7、R8）
- [ ] T043 [US4] 修改 `backend/api/rag.py` 的 C1 端点：按论文状态分派 `pending`／`approved`／`rejected` 三个分支，响应含 `revision_bumped` 与 `content_revision`（契约 C1）
- [ ] T044 [US4] 修改 `frontend/src/pages/AdminPage.tsx`：已批准论文的编辑弹窗显示升版警告，保存成功后按 `revision_bumped` 给出退回待审核提示（FR-017）
- [ ] T045 [P] [US4] 修改 `frontend/src/i18n/{zh,en}/admin.ts`：新增升版警告与退回提示文案

## 最终阶段：完善与跨故事事项

- [ ] T046 执行 `scripts/run-tests.sh frontend`、`go`、`backend` 与 `python -m pytest tests -q`，与 T003 基线比对确认无新增失败（SC-008）
- [ ] T047 执行 `cd frontend && npm run build`，确认 `tsc -b` 无类型错误
- [ ] T048 按 [quickstart.md](quickstart.md) 场景 1–8 手工走查，重点核对场景 5（升版）与场景 6（失败回滚）的数据库断言
- [ ] T049 验证升版重新批准后向量索引与知识图谱按新内容重建（quickstart 场景 5 步骤 10、SC-005、R9）
- [ ] T050 更新 Issue #76 正文：把「风险」中标记为阻塞点的唯一约束问题改为已解决结论（外键级联链方案，需一次迁移），并说明原「无数据库迁移」的判断已修正，使 Issue 与 Spec 一致
## 依赖与执行顺序

- **阶段 1**（T001–T004）阻断全部；T001、T002 是硬阻塞（#74 基建未就位则不得开始），T003 基线是 T046 判定回归的前提。
- **阶段 2**（T005–T011，外键级联链）阻断阶段 8（US4）——缺级联则任何升版操作都被 RESTRICT 外键拒绝。与阶段 3、4 无依赖，可并行。
- **阶段 3**（T012–T013，数据可见性）阻断阶段 5–8 的前端展示部分：缺预加载则编辑页拿不到 Tc、物性与结构。
- **阶段 4**（T014–T017，共享组件抽取）是纯重构，T016 必须全绿才能进入阶段 5；这是 US5 的 P1 底线。
- **阶段 5**（T018–T021）依赖阶段 3、4；T020 依赖 T014。
- **阶段 6**（T022–T030）依赖阶段 5；T028 阻断 T029，T029 阻断 T030。
- **阶段 7**（T031–T034）依赖阶段 6 的 T029（同文件端点扩展）。
- **阶段 8**（T035–T045）依赖阶段 2（级联）与阶段 6 的 T028、T029（同模块与同端点的分支扩展）。
- **最终阶段**（T046–T050）依赖全部前置阶段；T050 在文档与代码一致后执行。

**阶段 2 内部顺序**：T009、T010 写迁移 → T011 应用并核对 → T005–T008 运行时验证。注意多 CASCADE 冲突在建表期不报错，T011 的元数据核对不足以证明正确，必须靠 T005 的运行时级联测试。

**串行触点（同文件任务必须串行）**：

| 文件 | 涉及任务 | 跨 Feature 冲突 |
| --- | --- | --- |
| `frontend/src/components/UploadTaskEditor.tsx` | T015 | 与 #74 的 T018、#75 的 T010 冲突，须排在其后 |
| `frontend/src/pages/AdminPage.tsx` | T020、T030、T044 | 与 #74 的 T019、#75 的 T014 冲突，须排在其后 |
| `frontend/src/components/MaterialStatesEditor.tsx` | T014、T034 | 本 Feature 新增文件，无跨 Feature 冲突 |
| `backend/api/rag.py` | T029、T033、T043 | 本 Feature 内部串行；#74 已无新增端点，无跨 Feature 冲突 |
| `backend/services/scientific_draft_rewrite.py` | T028、T042 | 本 Feature 新增文件 |
| `goserver/handlers/admin.go` | T013 | 与 #74 的 `paperUpdateFields` 扩展冲突，须串行 |
| `frontend/src/i18n/{zh,en}/admin.ts` | T021、T045 | 与 #74、#75 的 admin 字典任务冲突 |
| `backend/tests/test_scientific_draft_rewrite.py` | T022–T026、T035–T039 | 同文件，须串行 |
| `tests/02_maintenance_and_verification/test_revision_cascade_chain.py` | T005–T008 | 本 Feature 新增文件 |
| `alembic/versions/<rev>_revision_cascade_chain.py` | T009、T010 | 本 Feature 新增文件 |

**并行机会**：阶段 2、3、4 三者互不影响，可并行；阶段 7 与阶段 8 在 T029 完成后可部分并行，但 `rag.py` 与 `scientific_draft_rewrite.py` 上的任务须串行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 / US1 | T018、T020 | 材料状态八项字段展示 |
| FR-002、FR-003、FR-004 / US1 | T012、T013、T019 | 预加载补齐 + Tc／物性／结构展示 |
| FR-005、FR-006、FR-007 / US2 | T027、T030 | 材料状态、Tc、物性的增删改 |
| FR-008 / US3 | T032、T034 | 结构附件删除 |
| FR-009、FR-010 / US3 | T031、T033、T034 | 结构补传与校验失败 |
| FR-011 / US2 | T027、T030 | 材料状态增删 |
| FR-012 / US2 | T022、T029 | 待审核论文原地保存 |
| FR-013 / US4 | T035、T042、T043 | 升版三字段单条 UPDATE |
| FR-014 / US4 | T005、T036、T042 | 外键级联自动更新血缘数据 |
| FR-015 / US4 | T040 | 升版后不对外公开 |
| FR-016 / US4 | T037、T042 | 升版审核事件 |
| FR-017 / US4 | T041、T044、T045 | 保存前升版告知 |
| FR-018 / US4 | T006、T028、T038、T042 | 单事务原子性与回滚（含级联回滚） |
| FR-019 | T030 | 两段保存的失败语义 |
| FR-020 / US2 | T024、T029 | 校验规则复用 |
| FR-021 / SC-007 | T029、T031、T033、T039 | 权限与状态限制 |
| FR-022 / US5 | T015、T016 | 上传链路不回退 |
| FR-023 | T014、T017 | 共享组件复用 |
| SC-001 | T018 | 字段集一致 |
| SC-002 | T022 | 待审核保存持久性 |
| SC-003 | T035、T040 | 升版后下架 |
| SC-004 | T005、T036 | 血缘数据完整性 |
| SC-005 | T049 | 重新批准后索引重建 |
| SC-006 | T006、T038 | 失败回滚 |
| SC-007 | T039 | 权限拒绝 |
| SC-008 | T016、T046 | 上传测试全绿 |
| SC-009 | T005、T035 | 版本一致性约束成立 |
| 外键完整性 | T007、T008、T011 | 删除直连不放松保障、ON DELETE 未变 |

## MVP 与增量策略

1. 完成阶段 1–4：依赖确认、外键级联链就位、数据可见、共享组件抽出且上传链路全绿。
2. 完成阶段 5（P1）：管理员可看到完整科学数据——单独交付即有价值，审核者不必跨页面比对。
3. 完成阶段 6（P1）：待审核论文可编辑，这是最安全且最高频的编辑场景，MVP 到此完成。
4. 完成阶段 7、8（P2）：结构补传与已批准论文升版重审。
5. 最终阶段收尾验证，并把 Issue 正文的阻塞点结论与迁移范围对齐（T050）。

阶段 5 交付后可独立验收；阶段 6 缺失时管理员仍只能查看不能修改，但不影响既有审核流程。阶段 8 是风险最高的增量，放在最后使前序能力与外键级联均已充分验证。
