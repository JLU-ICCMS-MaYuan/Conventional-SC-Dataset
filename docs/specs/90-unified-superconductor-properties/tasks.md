# 实施任务：MaterialState 模块化物性与动态表单

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：契约与测试基线

- [ ] T001 [P] 在 `backend/tests/test_form_definitions.py` 建立定义 v1/v2、发布不可变、停用和 Schema 校验失败测试。
- [ ] T002 [P] 在 `backend/tests/test_property_modules.py` 建立四模块、记录核心字段、Tc 类型和 Conditions 组级规则测试。
- [ ] T003 [P] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 建立模块增删和动态字段失败测试。
- [ ] T004 [P] 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 建立旧材料、Tc、物性、Conditions 和 Evidence 迁移 fixture。
- [ ] T005 [P] 在 `goserver/handlers/paper_detail_test.go` 与 `goserver/handlers/stats_test.go` 建立目标详情和 Tc 图表回归测试。

## 阶段 2：Expand Schema

- [ ] T006 创建基于当前 Alembic head 的 Expand 迁移，新增 `property_modules`、`property_records`、`form_definitions`、`property_record_evidences` 和迁移映射表。
- [ ] T007 在 Expand 迁移中建立 PropertyRecord 核心列、同 revision 外键、Tc CHECK、代表唯一键和图表索引。
- [ ] T008 将 `calculation_contexts`、`experimental_contexts` 的目标名称和引用迁移为 `calculation_conditions`、`experimental_conditions`，保留旧读取阶段所需兼容视图或适配器。
- [ ] T009 为 `chemical_systems`、`superconductors` 建立论文 revision 归属和目标范围唯一键，暂不删除旧全局唯一键。
- [ ] T010 同步 `backend/models.py` 与 `goserver/models/models.go` 的 Expand 阶段模型。
- [ ] T011 为四模块、预测/测量 Tc 和现有规范物性准备不可变 v1 定义种子及校验和。

## 阶段 3：定义服务与统一校验

- [ ] T012 [US4] 在 `backend/services/form_definition_service.py` 实现定义读取、版本选择、校验和和状态规则。
- [ ] T013 [US4] 在 `backend/api/form_definitions.py` 实现当前/指定版本读取及超级管理员发布、停用接口和审计。
- [ ] T014 [US4] 在 `backend/ingest/form_definitions.py` 实现受限 JSON Schema 和组级规则校验，拒绝脚本或未知关键字。
- [ ] T015 [US4] 在 `frontend/src/lib/formDefinitions.ts` 实现定义类型、缓存和校验和检查。
- [ ] T016 [US4] 在 `frontend/src/components/SchemaDrivenRecordForm.tsx` 用现有 UI 组件生成字段、条件显示和错误定位。
- [ ] T017 [US4] 用共享 fixture 验证前端显示规则与后端提交校验一致，并覆盖定义 v1/v2 共存。

## 阶段 4：Copy 与 Reconcile

- [ ] T018 [US5] 实现旧共享 `ChemicalSystem`、`Superconductor` 按实际引用论文 revision 复制及 ID 映射。
- [ ] T019 [US5] 重连 `MaterialState` 到论文拥有的材料，并验证论文 A/B 的 LaH10 主键和生命周期隔离。
- [ ] T020 [US2] 将旧理论/实验 Tc 分别迁为 `predicted_tc`、`measured_tc`，保留方法、值、代表标记和 Conditions。
- [ ] T021 [US1] 将旧普通物性按定义映射到四模块，无法确定模块或定义的记录进入异常报告。
- [ ] T022 [US3] 将旧 lambda、omega_log、mu_star 条件列迁为独立记录并保留正确 Conditions，不复制 Tc Evidence。
- [ ] T023 [US6] 合并两类旧 Evidence 连接到 `property_record_evidences`，保留旧 ID 到新 ID 映射。
- [ ] T024 在 `tests/02_maintenance_and_verification/test_issue90_migration.py` 对记录数、值、单位、Conditions、Evidence 和代表 Tc 逐项对账。
- [ ] T025 在隔离 MySQL 验证 Expand、分批 Copy、重复执行、故障恢复和迁移异常报告。

## 阶段 5：模块化写入与编辑

- [ ] T026 [US1] 在 `backend/ingest/property_modules.py` 实现模块与 PropertyRecord 规范化、核心字段/JSON 单一来源检查。
- [ ] T027 [US2] 在统一校验入口实现预测/测量 Tc、方法、Conditions 类型和代表唯一规则。
- [ ] T028 [US3] 实现 Conditions 内容归并、决定性输入分组和同组规则校验。
- [ ] T029 [US6] 更新 `backend/ingest/scientific_drafts.py`、`backend/api/rag.py` 和 `backend/services/scientific_draft_rewrite.py` 只写模块化目标模型。
- [ ] T030 [US1] 在 `frontend/src/lib/propertyModules.ts` 定义模块、记录和 Conditions 契约及稳定键管理。
- [ ] T031 [US1] 新增 `frontend/src/components/PropertyModuleEditor.tsx`，按需添加四模块并保证一条事实单一归属。
- [ ] T032 [US2] 重构 `frontend/src/components/MaterialStatesEditor.tsx`，复用动态记录表单编辑多条预测/测量 Tc。
- [ ] T033 [US2] 实现切换记录类型或方法时对不适用字段的明确清理、迁移预览或阻断错误。
- [ ] T034 [US6] 更新上传和管理员编辑页，共用同一模块组件、定义缓存和后端错误路径。

## 阶段 6：读取、搜索与图表切换

- [ ] T035 [US6] 更新 Go 详情批量预加载模块、记录、Conditions、定义版本和 Evidence，避免 N+1 查询。
- [ ] T036 [US6] 更新详情、探索和社区前端直接消费 `property_modules[]`，删除三来源拼装。
- [ ] T037 [US5] 更新本地材料搜索按规范化学式和组成聚合论文内材料，不依赖共享材料主键。
- [ ] T038 [US6] 更新 `goserver/handlers/stats.go` 从 PropertyRecord 固定列查询 Tc，保留方法和代表筛选。
- [ ] T039 [US6] 比较新旧详情、搜索和图表结果并检查 MySQL 查询计划使用目标索引。
- [ ] T040 [US6] 更新论文审核、升版、重写和物理删除拓扑，验证不会影响其他论文同名材料。

## 阶段 7：兼容、观察与 Contract

- [ ] T041 实现旧草稿和旧响应到模块化契约的单向边界转换，无法确定定义时显式报错。
- [ ] T042 递增上传缓存 Schema version；旧缓存转换后只产生新契约。
- [ ] T043 在目标环境确认新写入无旧表写入、详情/搜索/图表无差异并记录观察结果。
- [ ] T044 创建独立 Contract 迁移，退役 `tc_results`、`superconductor_properties`、旧 Evidence 连接和旧 Conditions 物性列。
- [ ] T045 在 Contract 迁移中删除被目标范围唯一键替代的材料全局唯一键，并验证恢复步骤。
- [ ] T046 在隔离 MySQL 完成 Expand -> Copy -> Switch -> Contract 和最近稳定阶段恢复验证。

## 阶段 8：验收与文档

- [ ] T047 [P] 按 `quickstart.md` 完成模块、Tc 配对、定义版本、双论文材料、迁移和下游人工验收。
- [ ] T048 [P] 运行 Python、Go、Vitest、前端构建、迁移专项和 `git diff --check`。
- [ ] T049 使用 `big-project-overview-maintainer` 按实际实现更新上传、维护与验证、搜索与图表 Overview。
- [ ] T050 使用 `big-project-issue-manager` 更新 #90 验收证据和 Documentation Impact，满足全部门槛后关闭 Issue。

## 依赖顺序

- T001–T005 固定失败契约；T006–T011 完成前不得复制数据。
- T012–T017 完成后才能让新记录绑定定义版本。
- T018–T025 必须在写入和读取切换前完成并对账。
- T026–T034 先切写入，T035–T040 再切公开读取和下游。
- T043 观察通过后才能执行 T044–T046 的旧结构退役。
- Overview 只能在实现与验证后更新，T049 阻断 T050。

## 需求覆盖

| 需求 | 任务 |
| --- | --- |
| FR-001–FR-006 | T002、T003、T021、T026、T030–T032 |
| FR-007–FR-012 | T002、T020、T022、T027–T033 |
| FR-013–FR-019 | T001、T011–T017、T026、T033 |
| FR-020–FR-022 | T004、T009、T018、T019、T037、T040、T045 |
| FR-023–FR-030 | T004–T011、T020–T025、T029、T034–T046 |
| FR-031–FR-033 | T002、T007、T013、T014、T040 |
| FR-034–FR-035 | T047–T050 |
