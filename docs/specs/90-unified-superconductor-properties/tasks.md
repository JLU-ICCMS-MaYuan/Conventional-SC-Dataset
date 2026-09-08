# 实施任务：MaterialState 模块化物性与动态表单

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备与失败契约

- [x] T001 [P] 在 `tests/fixtures/issue90/form-definition-matrix.json` 建立定义版本、方法字段、内嵌 Conditions、参数、预留扩展分组及错误结果的共享 fixture。
- [x] T002 [P] 在 `backend/tests/test_form_definitions.py` 建立发布不可变、停用、Schema 校验、升级与回滚失败测试。
- [x] T003 [P] 在 `backend/tests/test_issue90_properties.py` 建立记录类型、四种值类型边界、记录内条件参数失败及旧草稿转换测试。
- [x] T004 [P] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 建立模块增删、动态字段、重复运行和字段错误定位测试。
- [x] T005 [P] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 建立旧材料、Tc、物性、Conditions、Evidence 和增量写入 fixture。
- [x] T006 [P] 在 `goserver/handlers/paper_detail_test.go` 与 `goserver/handlers/stats_test.go` 建立目标详情、Tc 图表和查询数量回归测试。

## 阶段 2：基础 Schema 与共同契约

- [x] T007 在 `alembic/versions/20260907_issue90_expand_modular_property_schema.py` 创建模块、统一记录、定义、升级事件、证据连接、影子材料表和迁移映射表，并建立外键、CHECK、唯一键与索引。
- [x] T008 在 `backend/models.py` 映射 Expand 模型、记录 payload 内互斥条件对象、参数与分组及定义升级事件关系。
- [x] T009 在 `goserver/models/models.go` 映射目标只读模型和稳定 JSON 字段。
- [x] T010 在 `backend/data/form_definitions.v1.json` 定义四模块、预测/测量 Tc、普通物性的不可变 v1 种子。
- [x] T011 在 `backend/ingest/upload_contracts.py` 定义统一模块、记录、Conditions、定义版本和稳定错误响应类型。

## 阶段 3：用户故事 1 - 按需添加物性模块（P1）

- [x] T012 [US1] 在 `backend/ingest/property_modules.py` 实现模块规范化、单一归属、空模块删除和非空模块删除保护。
- [x] T013 [US1] 在 `frontend/src/lib/propertyModules.ts` 定义模块、记录和稳定键契约。
- [x] T014 [US1] 在 `frontend/src/components/PropertyModuleEditor.tsx` 实现四模块按需添加、排序和显式记录删除。
- [x] T015 [US1] 在 `frontend/src/components/MaterialStatesEditor.tsx` 接入模块编辑器并移除空模块占位提交。
- [x] T016 [US1] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证四模块独立往返、非空删除保护和其他模块数据不变。

**独立验收**：仅启用模块与通用记录契约，完成 Quickstart 场景一；不要求先切换历史数据或公开读取。

## 阶段 4：用户故事 2 - 录入多条预测和测量 Tc（P1）

- [x] T017 [US2] 在 `backend/ingest/property_modules.py` 实现 Tc 记录类型、方法、规范单位、非负值、代表唯一和 Conditions 类型校验。
- [x] T018 [US2] 在 `backend/ingest/scientific_drafts.py` 接入模块化草稿保存契约。
- [x] T019 [US2] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 实现动态记录编辑与条件错误提示。
- [x] T020 [US2] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证多 Tc、错配、双代表和方法切换行为。

**独立验收**：在新建材料状态中完成 Quickstart 场景三，验证多条 Tc 和非法组合，不依赖迁移旧记录。

## 阶段 5：用户故事 3 - 每条 Tc 自带完整资料（P1）

- [x] T021 [US3] 在 `backend/ingest/form_definitions.py` 实现记录内 Conditions、参数类型/单位/适用性与预留分组的 Schema 校验。
- [x] T022 [US3] 在 `frontend/src/lib/formDefinitions.ts` 实现客户端校验与嵌套错误路径映射。
- [x] T023 [US3] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 实现当前 Tc 的条件/参数一体填写及深复制，新 record_key 与复制资料互不联动。
- [x] T024 [US3] 在 `backend/tests/test_property_modules.py` 与 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 验证多条 Tc 的参数和网格展宽往返、复制修改隔离及相同内容不合并。

**独立验收**：完成 Quickstart 场景二；Tc-A/Tc-B 内资料完整，修改副本不影响原记录，相同内容保持独立。

## 阶段 6：用户故事 4 - 版本化 Schema 表单（P1）

- [x] T025 [US4] 在 `backend/services/form_definition_service.py` 实现草稿版本分配、发布不可变、停用和校验和规则。
- [x] T026 [US4] 在 `backend/api/form_definitions.py` 实现公开读取及超级管理员创建、发布和停用接口。
- [x] T027 [US4] 在 `frontend/src/lib/formDefinitions.ts` 实现按定义键、版本和校验和缓存键及不可用提示。
- [x] T028 [US4] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 根据记录类型生成字段、选项、单位提示和条件显示。
- [x] T029 [US4] 在 `backend/services/property_record_upgrade_service.py` 实现定义升级 preview/apply、前后快照、校验和并发检查和事件式 rollback。
- [x] T030 [US4] 在 `backend/api/form_definitions.py` 实现记录定义升级 preview/apply/rollback 接口和超级管理员权限校验。
- [x] T031 [US4] 在 `backend/tests/test_form_definitions.py` 验证方法特有定义键、v1/v2 并存、升级回滚、过期事件冲突和无部分写入。
- [x] T032 [US4] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 使用共享 fixture 验证前端显示与后端校验矩阵一致。

**独立验收**：完成 Quickstart 场景四；历史记录保留 v1，新记录使用 v2，升级可回滚且过期操作被拒绝。

## 阶段 7：用户故事 5 - 每篇论文拥有独立材料记录（P1）

- [x] T033 [US5] 在 `alembic/versions/20260907_issue90_copy_property_records.py` 按论文 revision 向影子材料表复制 `ChemicalSystem`、`Superconductor`，保存 MaterialState 旧新 ID 映射；切换前保持旧外键不变。
- [x] T034 [US5] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 验证论文 A/B 的 LaH10 主键、revision 外键、升版和删除隔离。
- [x] T035 [US5] 在 `backend/rag/search/sql_search.py` 与 `goserver/handlers/papers.go` 改用规范化学式和组成聚合跨论文结果。
- [x] T036 [US5] 在 `backend/services/scientific_draft_rewrite.py` 与 `goserver/handlers/paper_deletion.go` 更新升版、重写和物理删除拓扑，限制为当前论文 revision。

**独立验收**：完成 Quickstart 场景五；两篇论文的同名材料可以分别修改、升版、删除并同时被搜索。

## 阶段 7a：用户故事 7 - 自定义性质保留与管理员提升（P1）

- [x] T056 [US7] 在 `backend/tests/test_form_definitions.py` 与 `backend/tests/test_property_modules.py` 先建立自定义四种值类型保留、普通管理员提升成功、普通用户拒绝、重复请求、代码冲突与旧记录不变的失败测试。
- [x] T057 [US7] 在 `tests/fixtures/issue90/form-definition-matrix.json`、`tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `goserver/handlers/paper_detail_test.go` 先建立用户自定义录入、审核不提升仍保留、详情保留自定义字段、新定义供其他用户选择的前后端测试矩阵。
- [x] T058 [US7] 在 `backend/data/form_definitions.v1.json`、`backend/ingest/property_modules.py` 与 `backend/ingest/upload_contracts.py` 增加每模块已发布自定义模板、论文内 custom_property_key 校验和核心 Schema，保留原名、四种类型、单位及 Evidence。
- [x] T059 [US7] 在 `alembic/versions/20260907_issue90_expand_modular_property_schema.py` 与 `backend/models.py` 增加自定义性质键和提升事件表，落实来源快照、代码命名唯一、幂等唯一、来源重复提升约束。
- [x] T060 [US7] 在 `backend/services/form_definition_service.py` 与 `backend/api/form_definitions.py` 实现管理员直接提升、受限模板生成发布 v1、事务审计、来源并发检查、错误码和全站定义选择器接口。
- [x] T061 [US7] 在 `frontend/src/components/PropertyModuleEditor.tsx`、`frontend/src/components/SchemaDrivenRecordForm.tsx` 与 `frontend/src/pages/AdminPaperEditPage.tsx` 接入自定义录入、审核保留及批准后独立提升操作，提交成功刷新定义选择器。
- [x] T062 [US7] 在 `goserver/models/models.go`、`goserver/handlers/papers.go` 与 `frontend/src/lib/paperDetailView.ts` 保留自定义性质名称、类型、值、单位、键和 Evidence，隔离未规范化性质的跨论文聚合并防止公开审计信息。
- [x] T063 [US7] 运行 `backend/tests/test_form_definitions.py`、`backend/tests/test_property_modules.py`、`tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `goserver/handlers/paper_detail_test.go` 的预建用例，验证普通管理员无需超级管理员即可发布、历史绑定不变、源删除不影响通用定义。

**独立验收**：完成 Quickstart 场景九；用户自定义数据审核后可保留，普通管理员选择提升后其他用户可录入。
T056–T057 先于实现，T059 随基础迁移一起完成；T058、T060–T062 依赖 US1/US4，T063 阻断 T049–T055 收尾。

## 阶段 8：用户故事 6 - 统一上传、管理和公开读取（P2）

- [x] T037 [US6] 在 `backend/scripts/migrate_issue90_properties.py` 实现 Tc、普通物性和 Conditions/参数的幂等 Copy，并保存源字段到目标记录字段映射和异常报告。
- [x] T038 [US6] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 验证按源/目标组合的 Copy 幂等、预期参数复制、核心值、字段证据、代表 Tc、异常阻断及归档保留。
- [x] T039 [US6] 在 `backend/ingest/scientific_drafts.py`、`backend/api/rag.py` 与 `backend/services/scientific_draft_rewrite.py` 统一模块化写入并移除正常请求的旧字段写入。
- [x] T040 [US6] 在 `frontend/src/components/UploadTaskEditor.tsx`、`frontend/src/components/PaperEditView.tsx` 与 `frontend/src/pages/AdminPaperEditPage.tsx` 共用模块编辑器、定义缓存和后端错误路径。
- [x] T041 [US6] 在 `goserver/handlers/papers.go` 批量预加载模块、含 Conditions/参数的记录、定义版本和 Evidence，并避免 N+1 查询。
- [x] T042 [US6] 在 `frontend/src/lib/paperDetailView.ts`、`frontend/src/pages/PaperDetailPage.tsx` 与 `frontend/src/pages/SearchPage.tsx` 直接消费模块化详情契约。
- [x] T043 [US6] 在 `goserver/handlers/stats.go` 从统一记录固定列查询 Tc，保留类型、方法和代表筛选。
- [x] T044 [US6] 在 `goserver/handlers/paper_detail_test.go` 与 `goserver/handlers/stats_test.go` 比较新旧详情、图表结果、查询次数和基准性能。

**独立验收**：以目标模型 fixture 完成 Quickstart 场景六和场景八，上传只读态、管理、详情、搜索与图表结果一致。

## 阶段 8a：预设分组字段与完整导出

- [x] T064 [US3] 在 `backend/tests/test_property_modules.py`、`tests/01_decentralized_uploading/material-states-editor.test.tsx` 和 `goserver/handlers/paper_detail_test.go` 先建立预留分组新增字段、审核后保留、越组/覆盖系统键拒绝和复制隔离测试。
- [x] T065 [US3] 在 `backend/ingest/property_modules.py`、`frontend/src/components/SchemaDrivenRecordForm.tsx` 与 `goserver/models/models.go` 实现分组内 extensions 条目、类型单位校验、原位置往返展示及论文审核保留，升级不得静默丢弃。
- [x] T066 [US6] 在 `goserver/handlers/material_state_export_test.go` 先建立完整包离线解析、定义及结构文件内嵌、字段 Evidence、公开权限、缺失资料错误和 revision 并发测试。
- [x] T067 [US6] 在 `goserver/handlers/material_state_export.go`、`goserver/main.go` 和 `frontend/src/pages/PaperDetailPage.tsx` 实现 MaterialState 导出路由、快照一致读取、完整资料打包及下载入口。
- [x] T068 [US6] 运行 T064/T066 预建测试并完成 Quickstart 场景十、十一，核验预设分组字段保留与离线包完整性，将证据记入 `docs/specs/90-unified-superconductor-properties/validation.md`。

**依赖与验收**：T064/T066 在对应实现前完成；T065 依赖 US2/US4，T067 依赖 US6 详情契约。
T068 阻断生产切换 T047 和收尾 T049–T055；新增字段和完整导出均属于 #90 必交付范围。

## 阶段 9：切换与旧模型退役

- [x] T045 在 `backend/ingest/upload_contracts.py` 与 `frontend/src/lib/paperProcessing.ts` 增加上传缓存 Schema 版本及旧草稿单向转换，转换失败返回明确错误。
- [x] T046 在 `backend/scripts/migrate_issue90_properties.py` 实现 Copy 进度、含修改与删除的最终同步、逐项 Reconcile、全部科学写入停写门、在途事务排空、影子材料表更名和外键重建及恢复检查点。
- [x] T047 在 `goserver/handlers/papers.go`、`goserver/handlers/stats.go` 与 `frontend/src/lib/paperDetailView.ts` 完成 Read switch；读取验收失败时恢复旧读取。
- [x] T048 在 `backend/ingest/scientific_drafts.py` 与 `backend/services/scientific_draft_rewrite.py` 完成 Write switch，通过读路径冒烟后才解除停写。
- [x] T049 在 `docs/specs/90-unified-superconductor-properties/validation.md` 记录目标环境无旧写入、详情/搜索/图表对比、停写窗口和恢复演练证据。
- [x] T050 在 `alembic/versions/20260907_issue90_contract_legacy_properties.py` 退役旧 Tc、普通物性、Evidence 连接、Context 表和两张 legacy 材料表；保留迁移检查点、逐条映射与异常清单作为只读审计元数据，不再改动已切换生效的论文内唯一键。
- [x] T051 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 运行预建测试验证 Expand -> Copy -> 最终增量 -> Read switch -> Write switch -> Observe -> Contract，并验证切写前恢复与切写后目标 Schema 检查点及日志重放均无已提交数据丢失。

## 阶段 10：收尾、验收与文档

- [x] T052 [P] 在 `docs/specs/90-unified-superconductor-properties/quickstart.md` 记录模块、Tc、Conditions、定义升级回滚、双论文材料、迁移和下游人工验收结果。
- [x] T053 [P] 在 `docs/specs/90-unified-superconductor-properties/validation.md` 记录 Python、Go、Vitest、前端构建、隔离 MySQL 迁移专项和 `git diff --check` 结果。
- [x] T054 在 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md`、`docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md` 与 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md` 按实际实现更新当前功能总览。
- [x] T055 使用 `big-project-issue-manager` 核对 `docs/specs/90-unified-superconductor-properties/validation.md`，将验收证据和 Documentation Impact 回写 Issue #90，并按用户要求保持 Issue 为 Open。

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
保留每条记录自己的完整 Conditions 和参数，并由不可变定义完成前后端一致校验。US5、US6 和切换仍是完成 #90 实施的必需
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
| FR-040–FR-041 | T064–T068 |
| SC-001–SC-003 | T016、T020、T024 |
| SC-004–SC-005、SC-012 | T001、T002、T025–T032 |
| SC-006–SC-011 | T034–T055 |
| SC-013–SC-014 | T056、T057、T063 |
| SC-015–SC-016 | T064、T066、T068 |
