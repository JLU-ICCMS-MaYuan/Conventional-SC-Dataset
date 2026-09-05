# 实施任务：统一材料状态的超导物性记录

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：先用失败测试固定平级结构和旧契约转换边界。

- [ ] T001 [P] 在 `backend/tests/test_superconductor_properties.py` 新增统一记录、Context 复用、冲突和旧结构去重的失败测试。
- [ ] T002 [P] 在 `goserver/handlers/paper_detail_test.go` 新增材料状态只返回 `superconductor_properties[]`、不返回三类旧科学字段的失败契约测试。
- [ ] T003 [P] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `tests/01_decentralized_uploading/paper-detail-form-parity.test.tsx` 新增单一平级列表的失败测试。
- [ ] T004 [P] 在 `tests/02_maintenance_and_verification/test_issue90_property_migration.py` 建立 λ、ωlog、μ* 回填、计数、幂等、Evidence 缺口和 downgrade fixture。

## 阶段 2：基础能力

**目的**：建立全部用户故事依赖的 Schema、领域规范化和持久化映射。

- [ ] T005 在 `alembic/versions/20260904_0001_unified_superconductor_properties.py` 增加通用物性的实验 Context 外键与结果级方法/判据列、Tc 结果级判据列和互斥约束，预置参数定义，回填 λ/ωlog/μ* 与实验 Tc 判据，核验后移除旧 Context 结果列，并提供可逆迁移和缺失 Evidence 报告。
- [ ] T006 [P] 同步 `backend/models.py` 和 `goserver/models/models.go` 的通用物性实验 Context 关系，并移除 Context 参数字段映射。
- [ ] T007 在 `backend/ingest/superconductor_properties.py` 实现 `SuperconductorPropertyRecord` 规范化、Context 键归并、冲突检测、Tc 特化校验和旧结构兼容转换。
- [ ] T008 在 `backend/ingest/scientific_drafts.py` 改为消费统一记录，按物性代码映射 Tc/通用物性、复用 Context，并为每条记录建立 Evidence。
- [ ] T009 在 `backend/services/scientific_draft_rewrite.py` 统一管理端读取、比较和整体重写快照，删除内部 `tc_results/properties/calculations/experiments` 双结构。
- [ ] T010 在 `backend/api/rag.py` 让草稿保存、提交和管理员科学数据接口共用统一校验入口及字段级错误格式。

## 阶段 3：用户故事 1——在一个列表中校对全部物性（P1，MVP）

**目标**：上传和管理端只呈现一个平级物性列表。

**独立验收**：Tc、λ、ωlog、μ*、DOS、Hc2、超导能隙和 energy above hull 共 8 条记录往返保存，页面没有物性分组。

### 测试

- [ ] T011 [P] [US1] 在 `backend/tests/test_upload_jobs.py` 和 `backend/tests/test_upload_workflow.py` 增加 AI 输出归一化及新草稿单一字段测试。
- [ ] T012 [P] [US1] 在 `tests/01_decentralized_uploading/upload-task-editor-classification.test.tsx` 验证论文级 `superconductor_kind` 不控制物性字段或分组。

### 实施

- [ ] T013 [US1] 在 `frontend/src/lib/paperProcessing.ts` 定义统一记录、值、Context 和 Evidence 类型，移除内部草稿对 `DraftTcResult` 与 `properties[]` 的并行依赖。
- [ ] T014 [US1] 在 `frontend/src/lib/superconductorProperties.ts` 实现前端统一规范化、旧响应转换和稳定 `record_key/context_key` 管理。
- [ ] T015 [US1] 重构 `frontend/src/components/MaterialStatesEditor.tsx` 为单一平级物性编辑器，保留按记录类型启用的 Tc 字段校验但不建立分组。
- [ ] T016 [US1] 更新 `frontend/src/components/UploadTaskEditor.tsx` 的提交校验和字段定位，统一使用 `material_states[].superconductor_properties[]`。
- [ ] T017 [US1] 更新 `frontend/src/pages/AdminPaperEditPage.tsx` 复用同一记录转换和编辑结构，不再用数据库 Context ID 手工重组 Tc。
- [ ] T018 [US1] 更新 `frontend/src/i18n/zh/upload.ts`、`frontend/src/i18n/en/upload.ts`、`frontend/src/i18n/zh/paperDetail.ts` 和 `frontend/src/i18n/en/paperDetail.ts`，删除“其他普通物性”分组文案并补充 Context 关联提示。

## 阶段 4：用户故事 2——保持 Context 对应关系（P1）

**目标**：解除类别分组后仍准确表达同一次计算或实验。

**独立验收**：`calc-a` 与 `calc-b` 两组 μ*—Tc 经上传、详情和管理员重写后不交换；冲突 Context 被定位拒绝。

### 测试

- [ ] T019 [P] [US2] 在 `backend/tests/test_scientific_drafts.py` 和 `backend/tests/test_scientific_draft_rewrite.py` 增加共享 Context、跨状态拒绝、孤立 Context 清理和事务回滚测试。
- [ ] T020 [P] [US2] 在 `tests/02_identity_governance/admin-scientific-data-edit.test.tsx` 增加关联 Context 同步编辑和无数据库 ID 输入控件测试。

### 实施

- [ ] T021 [US2] 在 `backend/ingest/superconductor_properties.py` 与 `backend/ingest/scientific_drafts.py` 完成请求内 Context 去重、同键一致性和跨材料状态保护。
- [ ] T022 [US2] 在 `frontend/src/lib/superconductorProperties.ts` 与 `frontend/src/components/MaterialStatesEditor.tsx` 同步同一 Context 的关联记录，避免重复输入和内容漂移。

## 阶段 5：用户故事 3——保持 Tc 专用约束（P1）

**目标**：Tc 平级后仍保留 #84 和代表结果规则。

**独立验收**：实验/理论 Context 错配和同方法双代表 Tc 同时被应用层与数据库拒绝。

### 测试

- [ ] T023 [P] [US3] 扩展 `backend/tests/test_scientific_drafts.py` 与 `tests/02_maintenance_and_verification/test_issue90_property_migration.py`，覆盖 Tc 方法、Context 互斥和代表唯一约束。
- [ ] T024 [P] [US3] 扩展 `tests/01_decentralized_uploading/material-states-editor.test.tsx`，覆盖 Tc 专用字段只由 `property_code=tc` 和 `tc_method` 控制。

### 实施

- [ ] T025 [US3] 在 `backend/ingest/superconductor_properties.py` 和 `backend/models.py` 保留并适配 #84 的 Tc 校验与 MySQL 约束。
- [ ] T026 [US3] 在 `frontend/src/components/MaterialStatesEditor.tsx` 将 Tc 方法、实验判据和代表标记作为单条记录字段渲染，不恢复 Tc 分组。

## 阶段 6：用户故事 4——统一详情和下游展示（P2）

**目标**：公开读取和各页面直接消费统一物性投影。

**独立验收**：上传、管理和详情对固定论文返回相同记录集合，Tc 图表数据不变。

### 测试

- [ ] T027 [P] [US4] 在 `goserver/handlers/paper_detail_test.go` 覆盖 Tc、参数、实验 Context、Evidence 和无 Context 物性的统一序列化。
- [ ] T028 [P] [US4] 在 `tests/03_data_search_and_database_discovery/paper-detail-view-sources.test.tsx` 和 `tests/02_identity_governance/admin-scientific-data-view.test.tsx` 覆盖直接消费统一列表。
- [ ] T029 [P] [US4] 在 `goserver/handlers/stats_test.go` 回归代表 Tc、方法筛选和公开 revision；在 `goserver/handlers/paper_deletion_test.go` 回归新外键删除拓扑。

### 实施

- [ ] T030 [US4] 在 `goserver/handlers/superconductor_properties.go` 实现 Tc 与通用物性的统一批量投影、Context 嵌入、Evidence 嵌入和稳定记录键。
- [ ] T031 [US4] 更新 `goserver/handlers/papers.go` 的预加载与详情响应，只在材料状态下输出 `superconductor_properties[]`，并删除顶层 `key_properties` 科学事实副本。
- [ ] T032 [US4] 更新 `frontend/src/lib/paperDetailView.ts`、`frontend/src/pages/SearchPage.tsx` 和 `frontend/src/pages/share.tsx` 直接消费统一记录，移除三来源拼装。
- [ ] T033 [US4] 更新 `goserver/handlers/paper_deletion.go` 和 `backend/services/scientific_draft_rewrite.py` 的删除顺序与孤立 Context 处理。

## 阶段 7：兼容、迁移与收尾

**目的**：完成单向兼容、真实数据库验证和当前功能文档回写。

- [ ] T034 在 `backend/ingest/upload_jobs.py` 实现旧 `tc_results/calculation_contexts/properties` 到统一列表的单向转换，并移除新 AI 输出中的旧分组提示。
- [ ] T035 在 `backend/ingest/upload_contracts.py` 和 `backend/ingest/upload_jobs.py` 递增上传状态/分段结果 schema version，确保旧 Redis 缓存进入兼容转换。
- [ ] T036 在 `alembic/versions/20260904_0001_unified_superconductor_properties.py` 与 `tests/02_maintenance_and_verification/test_issue90_property_migration.py` 完成隔离 MySQL `upgrade → downgrade → upgrade`、参数计数和幂等验证。
- [ ] T037 [P] 按 `quickstart.md` 完成上传、管理、详情、搜索、图表、Evidence、升版重审和删除的人工验收。
- [ ] T038 [P] 运行 `bash scripts/run-tests.sh backend`、`bash scripts/run-tests.sh go`、`bash scripts/run-tests.sh frontend`、`cd frontend && npm run build` 与 `git diff --check`。
- [ ] T039 使用 `big-project-overview-maintainer` 按实际实现更新 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md`、`upload-review-and-default-selection.md`、`docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md`、`mysql-schema-catalog.md`、`literature-and-record-review.md`、`docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`、`local-material-search.md` 和 `tc-history-and-pressure-charts.md`。
- [ ] T040 更新 GitHub Issue #90 的验收与 Documentation Impact；只有全部关闭门槛满足后才关闭 Issue。

## 阶段 8：结构引用与跨论文候选（P1）

**目的**：保持 `StructureModels[]` 与 `SuperconductorProperties[]` 平行，允许空结构引用，并在
录入条件满足时通过已公开结构候选复用不透明 `structure_ref`。

### 测试

- [ ] T041 [P] 在 `backend/tests/test_structure_reference.py` 覆盖化学式标准化、`0.01 GPa` 压强容差、空间群/方法匹配、最近排序、距离平局和空引用保存。
- [ ] T042 [P] 在 `tests/02_maintenance_and_verification/test_structure_reference_migration.py` 覆盖 `canonical_structures`、来源模型映射、跨论文引用、已批准当前 revision 可见性和来源失效保护。
- [ ] T043 [P] 在 `backend/api/rag_structure_reference_test.py` 与 `tests/02_identity_governance/structure-reference-prompt.test.tsx` 覆盖候选接口权限、候选响应、确认/跳过、不自动写入和多物性复用。

### 实施

- [ ] T044 在 `alembic/versions/20260904_0001_unified_superconductor_properties.py` 增加 `canonical_structures`、`structure_models` 映射及物性/Context 的规范结构外键和索引，提供 upgrade/downgrade 与来源引用保护。
- [ ] T045 在 `backend/models.py`、`goserver/models/models.go` 和 `backend/services/structure_reference.py` 实现全局身份、方法组合标准化、候选过滤/排序和不透明引用解析；查询只读已批准当前 revision。
- [ ] T046 在 `backend/api/rag.py` 增加 `GET /api/rag/structure-references/search`，校验当前草稿/论文权限，返回来源摘要和压强差，不在查询时创建或修改身份。
- [ ] T047 在 `backend/ingest/superconductor_properties.py`、`backend/ingest/scientific_drafts.py` 与 `backend/services/scientific_draft_rewrite.py` 接入 `structure_ref` 确认写入、记录/Context 一致性、空引用和来源可用性校验。
- [ ] T048 在 `frontend/src/lib/paperProcessing.ts`、`frontend/src/lib/superconductorProperties.ts`、`frontend/src/components/MaterialStatesEditor.tsx` 和新增 `frontend/src/components/StructureReferencePrompt.tsx` 实现候选提示、明确确认、跳过/清空和多条物性共享引用，不暴露数据库 ID。
- [ ] T049 在 `goserver/handlers/superconductor_properties.go`、`goserver/handlers/papers.go` 与 `frontend/src/lib/paperDetailView.ts` 输出统一 `structure_ref` 和可选来源摘要；在删除/升版流程中阻止或标记无来源规范身份，并完成 quickstart 场景八的集成回归。

### 独立验收

- [ ] T050 [P] 按 `quickstart.md` 场景八执行跨论文候选、确认、跳过、平局、来源失效和三条物性复用验收，并将证据记录到 Issue #90。

## 依赖与执行顺序

- T001–T004 可并行，先固定各层失败契约。
- T005–T010 是所有用户故事的阻断基础；迁移、ORM 和规范化入口必须先一致。
- US1、US2、US3 均修改统一规范化与编辑器，同一文件任务按编号串行。
- US4 在写入契约稳定后实施，Go 详情测试和前端读取测试可并行。
- T034–T036 完成后才能删除内部旧契约依赖。
- Overview 只能在实现和验证完成后执行，T039 阻断 T040。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001–FR-005 / US1 | T001、T003、T007、T011–T018 | 平级记录、统一字段、参数独立化和共享编辑器 |
| FR-006–FR-011 / US2 | T001、T007、T019–T022 | 空 Context、Context 复用、一致性和同 revision 关系 |
| FR-012–FR-016 / US3 | T023–T026 | Tc 方法、理论/实验互斥、代表记录和 Evidence |
| FR-017–FR-020 / US1/US4 | T008–T010、T013–T018、T027–T032 | 原文保留、统一接口、编辑与详情一致 |
| FR-021–FR-025 / US4 | T004–T007、T034–T036 | 旧输入转换、缓存版本、迁移和 Evidence 缺口报告 |
| FR-026–FR-029 / US4 | T029、T033、T036–T038 | 图表、删除、MySQL 和全栈回归 |
| FR-030 | T039–T040 | Overview 与 Issue 关闭门槛 |
| FR-031 / US1–US3 | T005–T010、T013–T026 | 结果级方法/判据与共享 Context 职责分离 |
| FR-032–FR-039 / US5 | T041–T049 | 平行结构集合、可空引用、全局身份、候选查询、确认写入和来源生命周期 |

## MVP 与增量策略

1. T001–T010 建立可验证的统一领域和持久化基础。
2. T011–T026 完成上传/管理平级编辑、Context 对应和 Tc 约束，形成 MVP。
3. T027–T033 切换公开详情和下游展示。
4. T034–T040 完成旧数据迁移、全量验证、Overview 和 Issue 收尾。
5. T041–T049 虽在文档末尾追加，但实施时必须在 T013/T015/T030 前执行；T041–T043 通过后才能进入
   T044–T047，T048/T049 依赖 API 和持久化契约稳定，T050 是最终结构验收。
