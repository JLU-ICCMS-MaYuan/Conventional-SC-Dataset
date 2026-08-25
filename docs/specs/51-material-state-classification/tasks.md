# 实施任务：材料状态多维分类目录与统一审核

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：冻结 #51 契约并标明旧 Spec 的后续修订边界。

- [x] T001 在 `docs/specs/23-paper-ingestion-classification/`、`docs/specs/45-paper-classification-evidence-scope/`、`docs/specs/46-upload-scientific-data-pipeline/` 和 `docs/specs/50-remove-phase-label/` 的冲突文档中加入 #51 替代说明。
- [x] T002 [P] 在 `tests/02_maintenance_and_verification/test_issue51_classification_schema.py` 建立目录 seed、外键、Check、别名唯一和唯一主结构家族的失败测试。
- [x] T003 [P] 在 `backend/tests/test_classification_catalog.py` 建立规范化向量、初始别名、元素种类数和旧值白名单的失败测试。

## 阶段 2：基础能力

**目的**：建立所有用户故事依赖的数据模型、规范化服务和共享契约。

- [x] T004 在 `alembic/versions/20260825_0012_material_state_classification.py` 创建目录、别名、材料状态关联、建议、证据、审计及 seed，扩展 `material_states` 并删除目标 `papers.referenced_materials` 列。
- [x] T005 [P] 同步 `backend/models.py` 与 `goserver/models/models.go` 的新表、字段、关系和只读生成列映射。
- [x] T006 在 `backend/services/classification_catalog.py` 实现确定性名称规范化、目录解析、初始映射、草稿选择校验和元素种类数计算。
- [x] T007 [P] 在 `frontend/src/lib/classifications.ts` 与 `frontend/src/lib/paperProcessing.ts` 定义统一目录、正式选择、待确认选择和材料维度类型。

## 阶段 3：用户故事 1——数据库候选与统一中文（P1，MVP）

**目标**：上传编辑器从数据库展开正式候选，中文/英文/别名得到同一规范项，未知名称进入待确认状态。

**独立验收**：输入 `hydride`、`氢化物` 或 `高压氢化物` 均显示“氢基超导体”；输入未知名称显示待确认，不出现静态英文列表。

### 测试

- [ ] T008 [P] [US1] 在 `goserver/handlers/classifications_test.go` 编写公开目录仅返回启用中文项及别名的失败测试。
- [x] T009 [P] [US1] 在 `tests/01_decentralized_uploading/upload-task-classification.test.tsx` 编写候选展开、别名定位、待确认、加载失败和无 datalist 的失败测试。
- [x] T010 [P] [US1] 在 `backend/tests/test_upload_jobs.py` 编写 LLM 材料家族候选按作用域归一到材料状态的失败测试。

### 实施

- [x] T011 [US1] 在 `goserver/handlers/classifications.go` 和 `goserver/main.go` 实现 `GET /api/classification-catalogs`。
- [x] T012 [US1] 在 `frontend/src/components/ClassificationAutocomplete.tsx` 实现共享 MUI 选择器的加载、别名、待确认和错误状态。
- [x] T013 [US1] 修改 `backend/ingest/upload_jobs.py` 的分段/汇总契约，生成材料状态级分类并保持引用工作内部化。
- [x] T014 [US1] 修改 `frontend/src/components/UploadTaskEditor.tsx`，删除论文级 `sc_type`/静态 datalist，把共享选择器放入每个材料状态并支持同材料批量应用。

## 阶段 4：用户故事 2——独立维度与正式持久化（P1）

**目标**：材料家族、结构家族、元素种类数、压力和材料维度按独立事实提交到正式科学 Schema。

**独立验收**：`LaH10 @ 150 GPa` 提交后家族 ID、元素数 2、压力、维度和结构家族关系可独立读取。

### 测试

- [ ] T015 [P] [US2] 在 `backend/tests/test_upload_workflow.py` 编写正式目录、待确认建议、结构多选、元素数和分类证据的事务失败测试。
- [ ] T016 [P] [US2] 在 `tests/01_decentralized_uploading/upload-task-classification.test.tsx` 编写材料维度、结构家族多选/主项和元素数只读显示测试。

### 实施

- [x] T017 [US2] 修改 `backend/api/rag.py`，验证新草稿契约、拒绝旧写格式并返回材料状态分类。
- [x] T018 [US2] 修改 `backend/ingest/scientific_drafts.py`，解析正式目录或建立待审核建议，计算元素种类数并持久化结构家族和分类证据。
- [x] T019 [US2] 完成 `frontend/src/components/UploadTaskEditor.tsx` 的材料维度、结构家族和元素种类数交互及响应式布局。

## 阶段 5：用户故事 5——引用工作仅后台保留（P1）

**目标**：引用工作继续参与后台排除误判，但普通界面和最终科学数据没有“引用材料”字段。

**独立验收**：固定分段同时含本文和引用材料时，普通草稿/正式状态只有本文对象，管理员证据仍有两种 scope。

### 测试

- [ ] T020 [P] [US5] 在 `backend/tests/test_upload_jobs.py` 和 `backend/tests/test_upload_workflow.py` 增加普通 DTO 零引用字段、管理员证据保留 scope 的回归测试。
- [x] T021 [P] [US5] 在 `tests/01_decentralized_uploading/upload-task-classification.test.tsx` 增加界面不渲染“引用材料”的回归测试。

### 实施

- [x] T022 [US5] 修改 `backend/ingest/upload_jobs.py`、`backend/api/rag.py`、Python/Go Paper 模型和正式论文序列化路径，只在管理员分类证据中保留 `referenced_work` 和 AI 原始名称。
- [x] T023 [US5] 修改 `frontend/src/components/UploadTaskEditor.tsx`、`frontend/src/pages/AdminPage.tsx` 和 `frontend/src/components/PaperEditView.tsx`，普通界面只显示本文规范分类。

## 阶段 6：用户故事 3——管理员审核与目录治理（P2）

**目标**：管理员处理建议，超级管理员治理目录并得到不可变审计；论文批准具有分类完整性门。

**独立验收**：管理员映射建议成功但不能创建正式项；超级管理员批准别名/新项并看到审计；分类不完整论文批准返回 409。

### 测试

- [ ] T024 [P] [US3] 在 `goserver/handlers/classifications_test.go` 编写建议映射、权限、别名冲突、终态幂等、合并审计和论文批准门失败测试。
- [ ] T025 [P] [US3] 在 `tests/01_decentralized_uploading/admin-classification-governance.test.tsx` 编写管理员建议处理和超级管理员目录治理交互测试。

### 实施

- [x] T026 [US3] 在 `goserver/handlers/classifications.go` 实现材料状态分类更新、建议读取/处理、超级管理员目录 CRUD/合并和审计查询。
- [x] T027 [US3] 修改 `goserver/handlers/admin.go`，删除旧 `superconductor_type` 写路径、预加载当前材料状态分类并在批准事务执行完整性检查。
- [x] T028 [US3] 修改 `goserver/main.go`，按管理员/超级管理员权限注册分类治理路由。
- [x] T029 [US3] 在 `frontend/src/pages/AdminPage.tsx` 接入材料状态分类和建议处理，移除 KeyProperty 类型编辑。
- [ ] T030 [US3] 在 `frontend/src/components/ClassificationGovernancePanel.tsx` 和 `frontend/src/pages/SuperAdminPage.tsx` 增加目录、别名、建议与审计治理面板。
- [x] T031 [US3] 修改 `frontend/src/components/PaperEditView.tsx`，按新材料状态契约显示规范分类并移除旧英文 Select。

## 阶段 7：用户故事 4——一次性兼容与确定性迁移（P2）

**目标**：旧草稿可打开并退出旧格式；有旧数据库时只迁移唯一匹配白名单值。

**独立验收**：旧草稿读取/保存后没有 `sc_type`；迁移 dry-run 报告能区分 ready、ambiguous、unmapped 和 conflict。

### 测试

- [ ] T032 [P] [US4] 在 `backend/tests/test_classification_catalog.py` 和 `backend/tests/test_upload_workflow.py` 编写旧草稿一次性转换及新 PUT 拒绝旧字段测试。
- [x] T033 [P] [US4] 在 `tests/02_maintenance_and_verification/test_issue51_classification_migration.py` 编写旧数据库唯一匹配、歧义、冲突和 dry-run 零写入测试。

### 实施

- [x] T034 [US4] 在 `backend/api/rag.py` 和 `backend/services/classification_catalog.py` 实现旧草稿读取转换、迁移警告和保存退出条件。
- [x] T035 [US4] 在 `backend/scripts/migrate_material_classifications.py` 实现显式双数据库、默认 dry-run、`--apply` 和 JSON 报告。

## 阶段 8：完善与跨故事事项

- [x] T036 更新 `docs/overview/02-data-model-and-maintenance/domain-model-and-schema.md`、`docs/overview/06-rag-literature-assistant/pdf-ingestion.md` 和 `docs/overview/04-authentication-and-review/` 的已实现事实。
- [ ] T037 对照 `quickstart.md` 运行 Python、Go、前端、Schema、构建和 `git diff --check`，只勾选真实通过的任务。
- [ ] T038 使用浏览器在桌面和 390px 宽度验证候选 portal、键盘操作、错误/空状态、文本不溢出和管理员治理流程。
- [x] T039 对照 FR-001–FR-024、SC-001–SC-008 和接口契约执行 converge，修正文档或追加收敛任务。
- [ ] T040 按 AGENTS.md 检查工作树、仅暂存 #51 文件、使用规定多行提交消息自动 Git commit，并把提交和验证结果回写 Issue #51；不自动 push 或关闭 Issue。

## 依赖与执行顺序

- T001–T003 无代码依赖；T002–T003 先建立失败测试。
- T004–T007 阻断全部用户故事；Schema、模型和规范化服务按顺序完成。
- US1 和 US2 组成 MVP；US5 依赖其新草稿契约并在管理员治理前完成。
- US3 依赖正式持久化和建议实体；US4 依赖稳定的新契约。
- 同一文件上的任务严格串行，尤其是 `UploadTaskEditor.tsx`、`rag.py`、`admin.go` 和共享模型。
- Overview 只能在实现与验证后更新，不能把未完成设计写成当前事实。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001–007 / US2 | T002–T007、T015–T019 | Schema、独立维度、元素计算与持久化 |
| FR-008–011 / US1 | T008–T014 | 数据库目录、确定性匹配和共享 UI |
| FR-012–014、FR-023–024 / US3 | T024–T031 | 权限、建议、证据、审计和批准门 |
| FR-015–016 / US5 | T020–T023 | 引用工作内部化与普通 DTO 清理 |
| FR-017–019 / US4 | T032–T035 | 旧草稿转换和旧数据库确定性迁移 |
| FR-020–022 / US1–US2 | T010、T013–T019 | 复合名称拆分、批量应用和正式对象契约 |
| SC-001–008 | T002–T003、T008–T010、T015–T016、T020–T021、T024–T025、T032–T039 | 多层测试与最终收敛 |

## MVP 与增量策略

1. 完成准备、Schema、模型和规范化服务。
2. 交付 US1 + US2：数据库候选和材料状态正式分类主路径。
3. 收敛 US5：引用材料不污染普通数据。
4. 交付 US3：管理员和超级管理员治理闭环。
5. 交付 US4：旧草稿与旧数据库有界兼容。
6. 更新 Overview、浏览器验收、收敛并提交。

## 阶段 9：收敛补项

- [ ] T041 [US3] [missing] 在 `goserver/handlers/classifications_test.go` 补齐目录仅返回启用项、角色权限、别名跨规范名冲突、建议终态幂等、合并迁移和审计事务的 API 集成测试，覆盖 T008/T024 未证明的真实边界。
- [ ] T042 [US2] [partial] 在 `backend/tests/test_upload_workflow.py` 使用真实测试数据库补齐正式目录、待确认建议、结构多选、元素数、审核证据和 `referenced_work` 管理员快照的提交事务测试，覆盖 T015/T020。
- [ ] T043 [US2] [partial] 在 `tests/01_decentralized_uploading/upload-task-classification.test.tsx` 补齐材料维度、结构家族多选/唯一主项、元素种类数只读和同材料批量应用交互，覆盖 T016。
- [ ] T044 [US3] [partial] 在 `frontend/src/components/ClassificationGovernancePanel.tsx` 增加正式目录重命名、停用和合并操作，并在 `tests/01_decentralized_uploading/admin-classification-governance.test.tsx` 覆盖超级管理员交互，完成 T030。
- [ ] T045 [US4] [partial] 在 `backend/tests/test_upload_workflow.py` 补齐旧草稿 GET 一次性转换及 PUT/submit 拒绝旧字段的接口测试，完成 T032。
- [ ] T046 [US1] [partial] 使用 fresh MySQL 和普通管理员/超级管理员测试账户执行 `quickstart.md`，完成桌面与 390px 登录态浏览器验收、目录 portal/键盘/失败状态检查及生产迁移前验证，覆盖 T037/T038；不得运行生产迁移。
