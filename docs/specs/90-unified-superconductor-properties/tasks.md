# 实施任务：MaterialState 模块化物性与动态表单

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备与失败契约

- [ ] T001 [P] 在 `tests/fixtures/issue90/form-definition-matrix.json` 建立定义版本、方法字段、Conditions 身份规则和错误结果共享 fixture。
- [ ] T002 [P] 在 `backend/tests/test_form_definitions.py` 建立发布不可变、停用、Schema 校验、升级与回滚失败测试。
- [ ] T003 [P] 在 `backend/tests/test_property_modules.py` 建立模块增删、四种值类型、Tc 类型和 Conditions 组级失败测试。
- [ ] T004 [P] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 建立模块增删、动态字段、重复运行和字段错误定位测试。
- [ ] T005 [P] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 建立旧材料、Tc、物性、Conditions、Evidence 和增量写入 fixture。
- [ ] T006 [P] 在 `goserver/handlers/paper_detail_test.go` 与 `goserver/handlers/stats_test.go` 建立目标详情、Tc 图表和查询数量回归测试。

## 阶段 2：基础 Schema 与共同契约

- [ ] T007 在 `alembic/versions/20260907_issue90_expand_modular_property_schema.py` 创建模块、统一记录、定义、升级事件、两类 Conditions、证据连接、影子材料表和迁移映射表，并建立复合外键、CHECK、唯一键与索引。
- [ ] T008 在 `backend/models.py` 映射 Expand 模型、两个互斥 Conditions 外键及定义升级事件关系。
- [ ] T009 在 `goserver/models/models.go` 映射目标只读模型和稳定 JSON 字段。
- [ ] T010 在 `backend/data/form_definitions.v1.json` 定义四模块、预测/测量 Tc、既有规范物性及两类 Conditions 的不可变 v1 种子。
- [ ] T011 在 `backend/ingest/upload_contracts.py` 定义统一模块、记录、Conditions、定义版本和稳定错误响应类型。

## 阶段 3：用户故事 1 - 按需添加物性模块（P1）

- [ ] T012 [US1] 在 `backend/ingest/property_modules.py` 实现模块规范化、单一归属、空模块删除和非空模块删除保护。
- [ ] T013 [US1] 在 `frontend/src/lib/propertyModules.ts` 定义模块、记录和稳定键契约。
- [ ] T014 [US1] 在 `frontend/src/components/PropertyModuleEditor.tsx` 实现四模块按需添加、排序和显式记录删除。
- [ ] T015 [US1] 在 `frontend/src/components/MaterialStatesEditor.tsx` 接入模块编辑器并移除空模块占位提交。
- [ ] T016 [US1] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证四模块独立往返、非空删除保护和其他模块数据不变。

**独立验收**：仅启用模块与通用记录契约，完成 Quickstart 场景一；不要求先切换历史数据或公开读取。

## 阶段 4：用户故事 2 - 录入多条预测和测量 Tc（P1）

- [ ] T017 [US2] 在 `backend/ingest/property_modules.py` 实现 Tc 记录类型、方法、规范单位、非负值、代表唯一和 Conditions 类型校验。
- [ ] T018 [US2] 在 `backend/ingest/scientific_drafts.py` 让草稿保存与正式提交使用统一 Tc 记录契约。
- [ ] T019 [US2] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 实现预测/测量 Tc、方法切换及不适用字段清理或阻断。
- [ ] T020 [US2] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证多 Tc、错配、双代表和方法切换行为。

**独立验收**：在新建材料状态中完成 Quickstart 场景三，验证多条 Tc 和非法组合，不依赖迁移旧记录。

## 阶段 5：用户故事 3 - 保持 Tc 与相关性质准确对应（P1）

- [ ] T021 [US3] 在 `backend/ingest/form_definitions.py` 实现 `identity_rules`、normalizer、cardinality 和 `group_rules` 的受限解析与整组校验。
- [ ] T022 [US3] 在 `frontend/src/lib/formDefinitions.ts` 实现同一规则 fixture 的客户端求值与错误路径映射。
- [ ] T023 [US3] 在 `frontend/src/components/MaterialStatesEditor.tsx` 实现创建、选择和维护不透明 `calc-`/`exp-` Conditions 键，不按内容自动合并。
- [ ] T024 [US3] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证两组 mu_star-Tc、同键冲突和相同输入重复运行。

**独立验收**：完成 Quickstart 场景二；`calc-a`/`calc-b` 不错配，输入相同的 `calc-c`/`calc-d` 仍保持独立。

## 阶段 6：用户故事 4 - 版本化 Schema 表单（P1）

- [ ] T025 [US4] 在 `backend/services/form_definition_service.py` 实现草稿编辑、版本分配、当前版本、发布不可变、停用和校验和规则。
- [ ] T026 [US4] 在 `backend/api/form_definitions.py` 实现公开读取及超级管理员创建、修改草稿、发布和停用接口。
- [ ] T027 [US4] 在 `frontend/src/lib/formDefinitions.ts` 实现按定义键、版本和校验和缓存，定义不可用时执行只读降级并阻止新写入。
- [ ] T028 [US4] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 根据 JSON Schema 与 UI Schema 生成字段、选项、单位提示和条件显示。
- [ ] T029 [US4] 在 `backend/services/property_record_upgrade_service.py` 实现定义升级 preview/apply、前后快照、revision/校验和并发检查和事件式 rollback。
- [ ] T030 [US4] 在 `backend/api/form_definitions.py` 实现记录定义升级 preview/apply/rollback 接口和超级管理员权限校验。
- [ ] T031 [US4] 在 `backend/tests/test_form_definitions.py` 验证方法特有定义键、v1/v2 并存、升级回滚、过期事件冲突和无部分写入。
- [ ] T032 [US4] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 使用共享 fixture 验证前端显示与后端校验矩阵一致。

**独立验收**：完成 Quickstart 场景四；历史记录保留 v1，新记录使用 v2，升级可回滚且过期操作被拒绝。

## 阶段 7：用户故事 5 - 每篇论文拥有独立材料记录（P1）

- [ ] T033 [US5] 在 `alembic/versions/20260907_issue90_copy_property_records.py` 按论文 revision 向影子材料表复制 `ChemicalSystem`、`Superconductor`，保存 MaterialState 旧新 ID 映射；切换前保持旧外键不变。
- [ ] T034 [US5] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 验证论文 A/B 的 LaH10 主键、revision 外键、升版和删除隔离。
- [ ] T035 [US5] 在 `backend/rag/search/sql_search.py` 与 `goserver/handlers/papers.go` 改用规范化学式和组成聚合跨论文结果。
- [ ] T036 [US5] 在 `backend/services/scientific_draft_rewrite.py` 与 `goserver/handlers/paper_deletion.go` 更新升版、重写和物理删除拓扑，限制为当前论文 revision。

**独立验收**：完成 Quickstart 场景五；两篇论文的同名材料可以分别修改、升版、删除并同时被搜索。

## 阶段 7a：用户故事 7 - 自定义性质保留与管理员提升（P1）

- [ ] T056 [US7] 在 `backend/tests/test_form_definitions.py` 与 `backend/tests/test_property_modules.py` 先建立自定义四种值类型保留、普通管理员提升成功、普通用户拒绝、重复请求、代码冲突与旧记录不变的失败测试。
- [ ] T057 [US7] 在 `tests/fixtures/issue90/form-definition-matrix.json`、`tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `goserver/handlers/paper_detail_test.go` 先建立用户自定义录入、审核不提升仍保留、详情保留自定义字段、新定义供其他用户选择的前后端测试矩阵。
- [ ] T058 [US7] 在 `backend/data/form_definitions.v1.json`、`backend/ingest/property_modules.py` 与 `backend/ingest/upload_contracts.py` 增加每模块已发布自定义模板、论文内 custom_property_key 校验和核心 Schema，保留原名、四种类型、单位及 Evidence。
- [ ] T059 [US7] 在 `alembic/versions/20260907_issue90_expand_modular_property_schema.py` 与 `backend/models.py` 增加自定义性质键和提升事件表，落实来源快照、代码命名唯一、幂等唯一、来源重复提升约束。
- [ ] T060 [US7] 在 `backend/services/form_definition_service.py` 与 `backend/api/form_definitions.py` 实现管理员直接提升、受限模板生成发布 v1、事务审计、来源并发检查、错误码和全站定义选择器接口。
- [ ] T061 [US7] 在 `frontend/src/components/PropertyModuleEditor.tsx`、`frontend/src/components/SchemaDrivenRecordForm.tsx` 与 `frontend/src/pages/AdminPaperEditPage.tsx` 接入自定义录入、审核保留及批准后独立提升操作，提交成功刷新定义选择器。
- [ ] T062 [US7] 在 `goserver/models/models.go`、`goserver/handlers/papers.go` 与 `frontend/src/lib/paperDetailView.ts` 保留自定义性质名称、类型、值、单位、键和 Evidence，隔离未规范化性质的跨论文聚合并防止公开审计信息。
- [ ] T063 [US7] 运行 `backend/tests/test_form_definitions.py`、`backend/tests/test_property_modules.py`、`tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `goserver/handlers/paper_detail_test.go` 的预建用例，验证普通管理员无需超级管理员即可发布、历史绑定不变、源删除不影响通用定义。

**独立验收**：完成 Quickstart 场景九；用户自定义数据审核后可保留，普通管理员选择提升后其他用户可录入。
T056–T057 先于实现，T059 随基础迁移一起完成；T058、T060–T062 依赖 US1/US4，T063 阻断 T049–T055 收尾。

## 阶段 8：用户故事 6 - 统一上传、管理和公开读取（P2）

- [ ] T037 [US6] 在 `alembic/versions/20260907_issue90_copy_property_records.py` 迁移 Tc、普通物性、Conditions、参数和 Evidence，并输出逐行异常与对账结果。
- [ ] T038 [US6] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 验证 Copy 幂等、核心值、Conditions、Evidence、代表 Tc 和异常报告。
- [ ] T039 [US6] 在 `backend/ingest/scientific_drafts.py`、`backend/api/rag.py` 与 `backend/services/scientific_draft_rewrite.py` 统一模块化写入并移除正常请求的旧字段写入。
- [ ] T040 [US6] 在 `frontend/src/components/UploadTaskEditor.tsx`、`frontend/src/components/PaperEditView.tsx` 与 `frontend/src/pages/AdminPaperEditPage.tsx` 共用模块编辑器、定义缓存和后端错误路径。
- [ ] T041 [US6] 在 `goserver/handlers/papers.go` 批量预加载模块、记录、Conditions、定义版本和 Evidence，并避免 N+1 查询。
- [ ] T042 [US6] 在 `frontend/src/lib/paperDetailView.ts`、`frontend/src/pages/PaperDetailPage.tsx` 与 `frontend/src/pages/SearchPage.tsx` 直接消费模块化详情契约。
- [ ] T043 [US6] 在 `goserver/handlers/stats.go` 从统一记录固定列查询 Tc，保留类型、方法和代表筛选。
- [ ] T044 [US6] 在 `goserver/handlers/paper_detail_test.go` 与 `goserver/handlers/stats_test.go` 比较新旧详情、图表结果、查询次数和基准性能。

**独立验收**：以目标模型 fixture 完成 Quickstart 场景六和场景八，上传只读态、管理、详情、搜索与图表结果一致。

## 阶段 9：切换与旧模型退役

- [ ] T045 在 `backend/ingest/upload_contracts.py` 与 `frontend/src/lib/paperProcessing.ts` 增加上传缓存 Schema 版本及旧草稿单向转换，转换失败返回明确错误。
- [ ] T046 在 `backend/scripts/migrate_issue90_properties.py` 实现 Copy 进度、含修改与删除的最终同步、逐项 Reconcile、全部科学写入停写门、在途事务排空、影子材料表更名和外键重建及恢复检查点。
- [ ] T047 在 `goserver/handlers/papers.go`、`goserver/handlers/stats.go` 与 `frontend/src/lib/paperDetailView.ts` 完成 Read switch；读取验收失败时恢复旧读取。
- [ ] T048 在 `backend/ingest/scientific_drafts.py` 与 `backend/services/scientific_draft_rewrite.py` 完成 Write switch，通过读路径冒烟后才解除停写。
- [ ] T049 在 `docs/specs/90-unified-superconductor-properties/validation.md` 记录目标环境无旧写入、详情/搜索/图表对比、停写窗口和恢复演练证据。
- [ ] T050 在 `alembic/versions/20260907_issue90_contract_legacy_properties.py` 退役旧 Tc、普通物性、Evidence 连接、Context 表、两张 legacy 材料表及临时映射，不再改动已切换生效的论文内唯一键。
- [ ] T051 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 运行预建测试验证 Expand -> Copy -> 最终增量 -> Read switch -> Write switch -> Observe -> Contract，并验证切写前恢复与切写后目标 Schema 检查点及日志重放均无已提交数据丢失。

## 阶段 10：收尾、验收与文档

- [ ] T052 [P] 在 `docs/specs/90-unified-superconductor-properties/quickstart.md` 记录模块、Tc、Conditions、定义升级回滚、双论文材料、迁移和下游人工验收结果。
- [ ] T053 [P] 在 `docs/specs/90-unified-superconductor-properties/validation.md` 记录 Python、Go、Vitest、前端构建、隔离 MySQL 迁移专项和 `git diff --check` 结果。
- [ ] T054 在 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md`、`docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md` 与 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md` 按实际实现更新当前功能总览。
- [ ] T055 使用 `big-project-issue-manager` 核对 `docs/specs/90-unified-superconductor-properties/validation.md` 并将验收证据和 Documentation Impact 回写 Issue #90，满足关闭门槛后关闭 Issue。

## 依赖顺序

- T001–T006 固定失败契约；T007–T011 是所有用户故事的共同基础。
- 用户故事章节按产品优先级排列，实际执行按技术依赖：基础阶段后先完成 US4 定义服务（T025–T031），
  再完成 US1、US2、US3，最后执行跨前后端矩阵 T032。T021–T022 可先提供规则校验，US3 的编辑和验收依赖 US2。
- T001–T006 必须预先包含各故事与恢复路径的失败场景；后续 T016、T020、T024、T031、T032、T034、
  T038、T044、T051 为运行现有测试并记录验收结果，不是延迟到实现后才编写测试。
- US5 的材料复制必须在 US6 复制物性前完成；US6 的读取实现可基于目标 fixture 开发，但生产切换依赖 US1–US5 全部通过。
- T046 最终对账通过后才能执行 T047；T047 读取验收通过后才能执行 T048；T049 观察通过后才能执行 T050。
- T054 只能记录真实落地行为，且阻断 T055。

## 并行机会

- T001–T006 修改不同测试或 fixture，可以并行。
- 基础阶段完成后，T025–T032 的定义服务可与 T033–T036 的论文内材料迁移并行，但数据库迁移和 `backend/models.py` 修改保持串行。
- T041–T044 的 Go 读取与前端详情消费可以并行开发，最终以同一目标 fixture 汇合。
- T052 与 T053 可并行收集证据，T054 必须等待最终行为确定。

## MVP 范围

MVP 为基础阶段 + US1 + US2 + US3 + US4：在新建材料状态中可以按需添加模块，录入多条 Tc，
保持 Conditions 配对，并由不可变定义完成前后端一致校验。US5、US6 和切换仍是关闭 #90 的必需
范围，但不阻止先验收不依赖历史迁移的新数据编辑闭环。US7 同样是本次确认的必交付范围，纳入新数据
编辑闭环；其验收不依赖历史迁移，发布切换前必须完成。

## 需求覆盖

| 需求 | 任务 |
| --- | --- |
| FR-001–FR-006 | T003、T007–T016 |
| FR-007–FR-012 | T003、T017–T024 |
| FR-013–FR-019 | T001、T002、T010、T021、T022、T025–T032 |
| FR-020–FR-022 | T005、T007、T033–T036 |
| FR-023–FR-030 | T005–T011、T033–T051 |
| FR-031–FR-033 | T002、T007、T017、T025–T031、T041 |
| FR-034–FR-035 | T049、T051–T055 |
| FR-032、FR-036–FR-039 | T056–T063 |
| SC-001–SC-003 | T016、T020、T024 |
| SC-004–SC-005、SC-012 | T001、T002、T025–T032 |
| SC-006–SC-011 | T034–T055 |
| SC-013–SC-014 | T056、T057、T063 |
