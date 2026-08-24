# 实施任务：论文附件晶体结构提取

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

**目的**：冻结契约和测试夹具，确保实现依赖 #46 的新草稿主链路。

- [ ] T001 [P] [US1] 在 `backend/tests/fixtures/structures/` 增加合法 CIF、合法 POSCAR、无扩展名 POSCAR 和非法结构夹具，并记录预期 ASE 元数据
- [ ] T002 [P] [US2] 在 `backend/tests/fixtures/papers/` 增加完整坐标、Wyckoff 展开、多压力和缺失/冲突结构 PDF/文本夹具
- [ ] T003 [P] 更新 `frontend/src/lib/paperProcessing.ts`、`backend/ingest/upload_contracts.py` 的结构候选 schema version 和公开字段白名单

## 阶段 2：基础能力

**目的**：建立唯一的结构解析、校验、标准化、等价比较和导出边界。

- [ ] T004 [P] [US1] 为 `backend/services/structure_candidates.py` 编写原生 CIF/POSCAR ASE 读取、元数据和文件级错误测试
- [ ] T005 [P] [US4] 为 `backend/services/structure_candidates.py` 编写原胞/惯用胞派生、四种导出组合和周期性结构等价比较测试
- [ ] T006 [US1] 实现 `backend/services/structure_candidates.py`：ASE 读写、pymatgen 标准化、固定容差、哈希、四种派生表示和错误语义
- [ ] T007 [US2] 实现 `backend/ingest/structure_extractor.py`：PDF 结构字段、表格证据、坐标类型、占位和结构条件的候选 DTO
- [ ] T008 [US2] 在 `backend/ingest/structure_extractor.py` 接入 pymatgen 空间群确定性展开，并记录独立 Wyckoff 输入和推导标识

## 阶段 3：用户故事 1——直接上传结构附件（P1，MVP）

**目标**：正文任务能够接收并校验 CIF/POSCAR 附件。

**独立验收**：合法附件形成候选并进入草稿，非法附件显示文件级错误且不产生可提交结构。

### 测试

- [ ] T009 [P] [US1] 为 `backend/ingest/upload_contracts.py` 和 `backend/tests/test_upload_workflow.py` 增加 CIF/POSCAR 后缀、无扩展名 POSCAR 和多文件角色测试
- [ ] T010 [US1] 为 `backend/tests/test_upload_jobs.py` 增加附件提取、候选保存、单文件失败不影响其他文件的集成测试

### 实施

- [ ] T011 [US1] 扩展 `backend/ingest/upload_contracts.py`、`frontend/src/components/MultiFileUploadPanel.tsx` 和上传 DTO，接受结构附件并保持一个正文约束
- [ ] T012 [US1] 在 `backend/ingest/upload_jobs.py` 接入原生附件结构候选提取、来源哈希和草稿保存

## 阶段 4：用户故事 2——从 PDF 正文与表格恢复全部结构（P1）

**目标**：从可搜索 PDF 的完整坐标或 Wyckoff 位点恢复全部可证实结构，并区分失败候选。

**独立验收**：完整坐标和确定性展开夹具恢复正确；不完整/冲突夹具不生成完整结构。

### 测试

- [ ] T013 [P] [US2] 为 `backend/tests/test_structure_extractor.py` 增加完整坐标、分数/笛卡尔坐标、表格页码和缺失/冲突测试
- [ ] T014 [US2] 为 `backend/tests/test_structure_extractor.py` 增加 Wyckoff 展开、部分占位、无序占位和空间群不一致测试
- [ ] T015 [US2] 为 `backend/tests/test_upload_jobs.py` 增加同论文多压力/物相/计算条件和 PDF/附件等价合并测试

### 实施

- [ ] T016 [US2] 扩展 `backend/ingest/pdf_extractor.py` 的可搜索文本/表格证据输出，保留页码和表格定位，不加入 OCR
- [ ] T017 [US2] 在 `backend/ingest/upload_jobs.py` 编排 PDF 候选、结构条件键、多来源等价合并和冲突状态
- [ ] T018 [US2] 将结构候选纳入 #46 的 `material_states[]` 草稿及 `backend/services/scientific_drafts.py` 新契约

## 阶段 5：用户故事 3——核对并提交结构候选（P1）

**目标**：用户逐个确认候选，提交事务原子写入新结构模型和 Evidence。

**独立验收**：未确认不入库；确认候选与论文 revision/Evidence 同事务落库；晚期失败整体回滚。

### 测试

- [ ] T019 [P] [US3] 为 `backend/tests/test_scientific_draft_structures.py` 增加确认、排除、人工修正和服务端重新校验测试
- [ ] T020 [US3] 为隔离 MySQL 提交测试增加 `StructureModel`、`StructureModelEvidence`、revision 一致性和晚期回滚场景
- [ ] T021 [US3] 为 `tests/01_decentralized_uploading/structure-candidates.test.tsx` 增加候选证据、确认状态和错误展示测试

### 实施

- [ ] T022 [US3] 扩展 `backend/api/upload_tasks.py` 和 `backend/ingest/upload_contracts.py` 的候选读写、确认、排除和公开白名单契约
- [ ] T023 [US3] 扩展 `backend/services/scientific_drafts.py`，只持久化已确认候选并在同一事务建立结构与 Evidence 连接
- [ ] T024 [US3] 在 `frontend/src/components/UploadTaskEditor.tsx` 新增 `StructureCandidatePanel.tsx`，支持证据核对、修正、确认/排除和错误状态

## 阶段 6：用户故事 4——选择晶胞表示与导出格式（P2）

**目标**：默认惯用胞预览，用户可选择原胞/惯用胞和 CIF/POSCAR 导出。

**独立验收**：四种组合均可下载并重新读取，原始附件不变。

### 测试

- [ ] T025 [P] [US4] 为 `backend/tests/test_structures_api.py` 增加四种导出组合、标签和原始附件不可变测试
- [ ] T026 [P] [US4] 为 `tests/01_decentralized_uploading/structure-candidates.test.tsx` 增加默认惯用胞和导出选择控件测试

### 实施

- [ ] T027 [US4] 在 `backend/api/papers.py` 或结构路由增加当前 revision 结构预览/导出接口，复用权限门并校验 `cell`/`format`
- [ ] T028 [US4] 扩展 `frontend/src/components/StructureViewer3D.tsx` 和候选面板，默认加载惯用胞并提供导出选择

## 阶段 7：用户故事 5——查看已审核的公开结构（P2）

**目标**：approved 当前 revision 的授权用户查看和导出结构，其他状态不泄露。

**独立验收**：权限矩阵覆盖 approved、pending、rejected、旧 revision 和管理员/上传者/普通用户。

- [ ] T029 [P] [US5] 为 `backend/tests/test_structures_api.py` 和 `tests/01_decentralized_uploading/structure-candidates.test.tsx` 增加论文权限矩阵、revision 和无泄露测试
- [ ] T030 [US5] 接入论文详情结构查询、3Dmol.js 公开预览和导出权限门，保持现有 approved/pending/rejected 语义

## 最终阶段：完善与跨故事事项

- [ ] T031 [P] 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md`、`docs/overview/03-crystal-structure-management/` 和根 `README.md`
- [ ] T032 [P] 按 `quickstart.md` 执行后端、前端、隔离 MySQL 和上传集成验证，记录真实结果
- [ ] T033 执行 `big-project-spec-runner analyze` 规则的 FR/SC/任务覆盖检查，修复文档矛盾后再进入 implement

## 依赖与执行顺序

- T001–T003 无代码依赖，可并行；T003 完成后冻结草稿 schema version。
- T004–T008 阻断所有用户故事；T006 是 T008 和 T011–T018 的科学校验依赖。
- US1 完成后才能验证原生附件；US2 依赖 US1 的候选 DTO，但可并行编写 PDF 提取单测。
- US3 依赖 #46 的新 scientific draft writer 和 US1/US2 候选；同一事务文件保持串行。
- US4 依赖 T006；US5 依赖 US3 正式结构和现有论文权限。
- T031–T033 必须在实现前完成文档一致性门；不以静态源码断言代替运行测试。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001–FR-003 / US1 | T004、T006、T009–T012 | 附件契约、ASE 校验和草稿接入 |
| FR-004–FR-010 / US2 | T007–T008、T013–T018 | PDF/表格字段、Wyckoff 展开和失败阻断 |
| FR-005、FR-017、FR-020 / US2 | T015、T017 | 多条件候选与等价合并 |
| FR-011、FR-021 / US4 | T005–T006、T025–T028 | 原胞/惯用胞和四种导出 |
| FR-013–FR-016 / US3 | T019–T024 | 候选确认、事务写入和 Evidence |
| FR-022–FR-023 / US5 | T029–T030 | approved 当前 revision 权限 |
| FR-018–FR-019 / 全部故事 | T010、T013–T015、T019–T021、T025、T029、T032 | 错误语义和自动化验证 |

## MVP 与增量策略

1. 完成 T001–T012，交付合法原生 CIF/POSCAR 上传、ASE 校验和候选草稿。
2. 完成 T013–T018，加入 PDF 完整坐标、Wyckoff 展开和多结构合并。
3. 完成 T019–T024，用户确认后接入 #46 单事务正式写入。
4. 完成 T025–T028，提供默认惯用胞和四种导出组合。
5. 完成 T029–T030，开放 approved 当前 revision 的结构查看和导出。
6. 完成 T031–T033 后才进入 implement；实现阶段按依赖逐项勾选任务。
