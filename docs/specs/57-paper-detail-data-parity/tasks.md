# 实施任务：论文详情数据一致性（后端读取契约补全）

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认修复前基线，使「修复后全绿」有对照意义。

- [x] T001 记录 Go 测试修复前基线：`docker run --rm -v /home/mayuan/code/SC-Wiki/goserver:/src -w /src -e GOFLAGS=-mod=mod -e GOPROXY=off -e CGO_ENABLED=1 scwiki-auth-test-cgo:latest sh -c 'go test ./... -count=1'`（已实测四包全绿，说明既有测试对本缺陷无感）

## 阶段 2：基础能力

**目的**：模型层改动。删除兼容字段会立即破坏 `papers.go` 与 `admin.go` 的编译，因此本阶段与阶段 3、4 构成一个不可分割的编译单元，必须连续完成到可编译状态再跑测试。

- [x] T002 `goserver/models/models.go`：为 `SuperconductorProperty` 补 `PropertyDefinition PropertyDefinition` 关联（`gorm:"foreignKey:PropertyDefinitionID"`），支撑 FR-005 的展示名取值
- [x] T003 `goserver/models/models.go`：删除 `:437-448` 的 12 个 `gorm:"-"` 兼容字段（`SuperconductorID`、`Name`、`NameNote`、`PressureGpa`、`TemperatureK`、`ConditionJSON`、`IsPrimary`、`SuperconductorType`、`ArticleType`、`SourceLabel`、`StructureText`、`StructureFormat`）

## 阶段 3：用户故事 1——提交者能完整复查提交的科学数据（P1，MVP）

**目标**：论文的 Tc 结果、计算上下文、材料状态全字段、物性真实名称可被读出。

**独立验收**：请求论文 4 详情，Tc=274、λ=2.56、μ*=0.1、压强 250/200/`above 200 GPa`、空间群 `Fm-3m`/225、物性名 `thermodynamic stability` 均可取得。

### 测试

- [x] T004 [US1] `goserver/handlers/paper_detail_test.go`（新建）：用 SQLite 内存库 `AutoMigrate` 并真实插入论文 + 材料状态 + Tc 结果 + 计算上下文 + 物性 + 物性定义，断言 `GetPaper` 响应含 `tc_results`（`tc_value_k`）与 `calculation_contexts`（`lambda_ep`、`mu_star`）。禁止用 `DryRun` 断言 SQL 文本（research D8）
- [x] T005 [US1] `goserver/handlers/paper_detail_test.go`：断言材料状态输出含压强值/下限/上限/原文/原文单位、报告空间群符号与群号、温度、磁场、`state_kind`、`note`；单臂区间用例断言 `pressure_max_gpa` 为 `null` 而非 0
- [x] T006 [US1] `goserver/handlers/paper_detail_test.go`：断言物性 `name` 取自 `property_definitions.display_name`，并有 `display_name` 缺失时回退 `name_raw` 的用例

### 实施

- [x] T007 [US1] `goserver/handlers/papers.go` `GetPaper`：补 Preload `MaterialStates.TcResults`、`MaterialStates.CalculationContexts`、`MaterialStates.Properties.PropertyDefinition`，保持单次请求内有界查询、不产生 N+1
- [x] T008 [US1] `goserver/handlers/papers.go` `materialStatesToDict`：补 data-model 列出的全部材料状态字段，并嵌套输出 `tc_results` 与 `calculation_contexts`（嵌套形态见 research D3）

## 阶段 4：用户故事 2——详情数据中不再出现恒零值字段（P1）

**目标**：响应中每个字段的值都来自数据库真实列。

**独立验收**：改动库中物性的 `name_raw` 后响应随之变化；响应不含 data-model 列出的 11 个已移除键。

### 测试

- [x] T009 [US2] `goserver/handlers/paper_detail_test.go`：断言响应的物性键集合不含 `superconductor_id`、`name_note`、`pressure_gpa`、`temperature_k`、`condition_json`、`is_primary`、`superconductor_type`、`article_type`、`source_label`、`structure_text`、`structure_format`

### 实施

- [x] T010 [US2] `goserver/handlers/papers.go` `keyPropertiesToDict`：`name` 改取 `PropertyDefinition.DisplayName` 回退 `NameRaw`；新增输出 `value_number`、`canonical_unit`；移除 11 个已删字段的序列化（依赖 T003，与 T008 同文件需串行）

## 阶段 5：用户故事 3——依赖同批数据的其他功能回到真实数据源（P1）

**目标**：记录搜索能返回真实结果；管理员物性修改能落库；前端消费方取到真实值。

**独立验收**：搜索接口日志不再报表不存在且对已批准数据返回行；管理员改物性后可在库中查证。

### 测试

- [x] T011 [US3] `goserver/handlers/paper_detail_test.go`：SQLite 真实插入已批准论文 + 材料状态 + Tc 结果，断言 `approvedRecordSearchQuery` 实际执行成功并返回该行（覆盖「表/列不存在」这一真实故障边界）
- [x] T012 [US3] `goserver/handlers/paper_detail_test.go`：断言压强与类型筛选基于 `material_states.pressure_value_gpa`、`state_kind` 求值，结果与插入数据一致；断言未批准论文不出现在结果中
- [x] T013 [US3] `goserver/handlers/paper_detail_test.go`：断言管理员物性更新写入真实列后可读回；断言无对应列的字段不被接受

### 实施

- [x] T014 [US3] `goserver/handlers/papers.go` `approvedRecordSearchQuery`：主表改 `tc_results`，JOIN `material_states` 与 `papers`，保留 `papers.review_status='approved'` 约束（映射表见 research D5）
- [x] T015 [US3] `goserver/handlers/papers.go` `SearchRecords` 的筛选分支：Tc 改 `tc_results.tc_value_k`、压强改 `material_states.pressure_value_gpa`、类型改 `material_states.state_kind`、元素改 `material_states.superconductor_id`，移除 `chart_only` 的主记录过滤（与 T014 同文件串行）
- [x] T016 [US3] `goserver/handlers/papers.go` `flatRecordToDict`：`pressure`、`type` 改取材料状态字段，`space_group` 由硬编码 `-` 改取 `reported_space_group_symbol`，`tc` 改取 `tc_value_k`（与 T015 同文件串行）
- [x] T017 [P] [US3] `goserver/handlers/admin.go`：`keyPropertyUpdateFields`（`:39-43`）与 `newKeyProperty`（`:265-283`）收敛为真实列，新增 `value_number`、`canonical_unit` 支持，移除 9 个无列字段（不转写到材料状态，理由见 research D6）
- [x] T018 [P] [US3] `frontend/src/components/ChartGroupEditor.tsx`：`:210-211`、`:467-468` 的 `kp.pressure_gpa`、`kp.superconductor_type` 改读所属材料状态的 `pressure_value_gpa`、`state_kind`，布局不变
- [x] T019 [P] [US3] `frontend/src/pages/share.tsx`：`:588` 移除 `is_primary` 主次高亮，`:591`、`:597` 的条件列改读材料状态，表格结构不变
- [x] T020 [P] [US3] `frontend/src/pages/AdminPage.tsx`：`:351` 的物性 payload 收敛为真实列，与 T017 的白名单一致
- [x] T021 [P] [US3] `frontend/src/components/PaperEditView.tsx`：`:127-133`、`:262-325` 的字段来源修正为真实值，**不做死代码清理**（组件去留属 #59，见 spec 范围外事项）

## 最终阶段：完善与跨故事事项

- [x] T022 Go 全量回归：T001 的同一命令，四包全绿（SC-006）
- [x] T023 前端全量回归：`cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit`（SC-006）
- [x] T024 重建并部署镜像：`cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build goserver frontend && docker compose -f dev.yaml up -d goserver frontend`；核对运行制品含本次改动
- [x] T025 按 [quickstart.md](quickstart.md) 场景 1、2、3 人工验收：论文 4 的 Tc/λ/μ*、压强区间、空间群、物性名称可见且无恒零值字段（SC-001、SC-002、SC-003）
  - 证据：在容器网络内对**真实 MySQL** 执行同一 Preload 链，读出 `tc_value_k=274`、`lambda_ep=2.56`、`mu_star=0.1`、`pressure_value_gpa=250`、`pressure_min_gpa=200`、`pressure_max_gpa=null`、`pressure_raw="above 200 GPa"`、`space_group=Fm-3m`/225、`prop_display_name="thermodynamic stability"`、`value_number=200`
- [x] T026 按 [quickstart.md](quickstart.md) 场景 4、5 人工验收：搜索日志不再报表不存在、管理员物性修改落库（SC-004、SC-005）
  - 证据：`/api/papers/search/records` 连续请求均 200，goserver 日志 `doesn't exist|no such column` 计数为 0（修复前每次请求必报 `Table 'scwiki.key_properties' doesn't exist`）；新 JOIN 在真实 MySQL 上返回 23 行真实记录，全部列可解析，接口返回空仅因全库无 `approved` 论文（spec 假设已声明）
- [x] T027 按 [quickstart.md](quickstart.md) 场景 6 人工验收：权限判定、图表分组编辑、分享页、空数据论文均无回归（FR-010）
  - 证据：匿名访问 `pending` 论文 403、不存在论文 404、无效 ID 400（#56 逐篇鉴权未变）；`/api/papers/stats/chart-data` 200；`/api/papers/search/all` 200；Go 四包与前端 8 文件 65 用例全绿、`tsc` 无输出
  - 遗留（**与本 Feature 无关，不构成回归**）：`external.go:182` 与 `papers.go:838` 分别报 `alexandria_element_idx`、`htsc2025_materials` 表不存在。两张外部数据集表在库中本就不存在，`external.go` 本次未改动，`searchHTSCAll` 也未被本 Feature 触及；属独立的外部数据集缺失问题
- [x] T028 使用 `big-project-overview-maintainer` 将「论文详情的读取契约与可见字段」「记录搜索的记录主体」回写 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-ingestion.md`，并在相关变更记录追加 Issue #57 链接
  - 实际回写 10 个文档：读取契约迁移使多处 Overview 成为错误的当前事实，一并纠正。含 `mysql-schema-catalog.md`（原称 `key_properties` 为「当前主要物性表约 1101 条」，实测该表不存在，已替换为 `superconductor_properties` 真实字段表并更新关系图）、`paper-and-property-results.md`（原称「新旧契约并存，待把 Go 搜索/详情投影切换到条件化表」，本 Feature 已完成该切换）、`local-material-search.md`、`literature-and-record-review.md`、`format-validation-and-storage.md`、`tc-history-and-pressure-charts.md` 及两处 README 导航
  - 标记「待核验」而非断言：`/api/structures/by-property/{kp_id}`（Python 侧，需登录未实测）与 `chart_group_items.key_property_id`（组合项 0 条，无非空场景可测）
- [x] T029 交由 `big-project-issue-manager` 回写 Spec 链接并在全部门槛满足后关闭 Issue #57

## 依赖与执行顺序

- T001 无依赖。
- T002、T003 阻断全部用户故事：删除字段后 `papers.go`、`admin.go` 立即编译失败，必须连续完成 T007–T010、T014–T017 才能恢复可编译状态。**在此之前无法运行任何测试**，因此测试任务 T004–T006、T009 虽先写，但只能在编译恢复后才可运行验证。
- 同文件串行：T007 → T008 → T010 → T014 → T015 → T016 均在 `goserver/handlers/papers.go`。
- T017 与 T018–T021 位于不同文件，可并行，且不阻断 Go 侧任务。
- T022、T023 依赖全部实施任务；T024 依赖 T022、T023；T025–T027 依赖 T024；T028 依赖 T025–T027 全部通过；T029 依赖 T028。
- `[P]` 标记的任务位于不同文件且无未完成依赖。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001 / US1 | T004、T007、T008、T025 | Tc 结果的 Preload、序列化与验收 |
| FR-002 / US1 | T004、T007、T008、T025 | 计算上下文同上 |
| FR-003 / US1 | T005、T008、T025 | 压强值/区间/原文，含单臂 null 语义 |
| FR-004 / US1 | T005、T008、T025 | 空间群、温度、磁场、`state_kind`、`note` |
| FR-005 / US1 | T002、T006、T010、T025 | 物性展示名关联与回退 |
| FR-006 / US2 | T003、T009、T010、T025 | 兼容字段删除，编译期保证无残留 |
| FR-007 / US3 | T011、T014、T026 | 搜索改真实表 |
| FR-008 / US3 | T012、T015、T016、T026 | 筛选列重映射与结果行来源 |
| FR-009 / US3 | T013、T017、T020、T026 | 管理员写入真实列或明确拒绝 |
| FR-010 / 全部 | T018–T021、T022、T023、T027 | 消费方适配与全量回归 |
| SC-001 | T004、T006、T025 | Tc=274、λ=2.56、μ*=0.1、名称非空 |
| SC-002 | T005、T025 | 250/200 GPa、`above 200 GPa`、`Fm-3m`/225 |
| SC-003 | T009、T025 | 字段与库逐项一致、无恒零值 |
| SC-004 | T011、T012、T026 | 搜索返回真实结果、无表不存在错误 |
| SC-005 | T013、T026 | 管理员修改可查证 |
| SC-006 | T022、T023 | Go 与前端全量通过 |
| 边界：空集合语义 | T004、T027 | 无 Tc 论文返回 `[]` |
| 边界：NULL 可区分 | T005 | `pressure_max_gpa` 为 null 而非 0 |
| 边界：多条计算上下文 | T004 | 含全 NULL 记录一并返回 |

## MVP 与增量策略

1. 完成 T001 基线记录与 T002、T003 模型改动。
2. 连续完成阶段 3、4、5 的实施任务直到可编译，再运行测试验证——这是本 Feature 的编译单元约束，不是可选顺序。
3. 三个用户故事在验收层面独立：故事 1、2 由详情接口证明，故事 3 由搜索与管理员路径证明，可分别验收。
