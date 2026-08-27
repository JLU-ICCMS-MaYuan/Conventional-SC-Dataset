# 实施计划：论文详情数据一致性（后端读取契约补全）

**GitHub Issue**：[#57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)

**日期**：2026-08-27

**Spec**：[spec.md](spec.md)

## 摘要

论文的正式科学数据已按条件化实体模型正确写入，但读取侧仍停留在旧 `key_properties` 的字段假设：详情接口不查 `tc_results` 与 `calculation_contexts`、材料状态被裁剪到 9 个字段、一批 `gorm:"-"` 兼容字段被当作真实数据序列化。同一批兼容字段还使记录搜索查询一张已不存在的表（用户可见的搜索恒为空），并使管理员修改物性静默失效。

方案是把读取契约整体迁移到真实数据源：补全 Preload 与序列化并将新数据段嵌套在材料状态之下、逐个定档 12 个兼容字段（能映射的改真实来源、不能映射的移除）、把记录搜索的记录主体从 `key_properties` 改为 `tc_results` JOIN `material_states`、把管理员物性写入白名单收敛为真实列。所有决策与实测依据见 [research.md](research.md)。

## 技术上下文

- **语言与版本**：Go 1.25.0（goserver）、TypeScript + React 18（frontend）
- **主要依赖**：Gin 1.12.0、GORM 1.31.2（driver/mysql 1.6.0、driver/sqlite 1.6.0）、MUI
- **数据存储**：MySQL 8.4，库名 `scwiki`；相关表 `papers`、`material_states`、`tc_results`、`calculation_contexts`、`superconductor_properties`、`property_definitions`、`structure_models`
- **测试体系**：Go 标准 `testing` + SQLite 内存库真实插入（`goserver/handlers/*_test.go`）；前端 Vitest（`npm run test:upload-ui`）。Go 测试命令见 [research.md](research.md) D8
- **目标平台**：Docker Compose dev 栈（`/home/mayuan/work/SC-Wiki-docker/dev.yaml`），服务名 `goserver`、`frontend`
- **性能目标**：详情接口新增数据段后仍为单次请求内的有界 Preload，不产生按材料状态数量放大的 N+1 查询
- **约束**：不改变写入契约与数据所有权；不改变 #56 已确立的逐篇后端鉴权；前端改动限于「取到真实值且不回归」，展示重构留给 #59
- **规模范围**：1 个 Go handler 文件、1 个 Go 模型文件、1 个 Go admin 文件、4 个前端消费方文件

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| Spec FR-006 | 不得输出与库内容无关的字段 | 12 个兼容字段逐个定档（research D4），能映射的改真实来源、其余从模型与序列化中一并删除，使「保留恒 null 键」在编译层不可能 | 通过 |
| Spec FR-009 / Skill 规则 | 不得悄悄改变数据所有权 | 管理员物性写入只收敛白名单到真实列，不把无列字段转写到材料状态（拒绝越过材料状态自身校验的间接写入，research D6） | 通过 |
| Spec FR-010 | 既有行为不回归 | `key_properties` 顶层键位置不变，仅修正内容；新增数据段一律走嵌套形态；Go 与前端既有测试全绿作为门槛 | 通过 |
| Skill 完成条件 4 | 真实生产路径 + 能覆盖实际故障边界的测试 | 新增测试用 SQLite 真实 `AutoMigrate`+`Create`+读取断言，不用 `DryRun` 断言 SQL 文本——本 Feature 的故障边界正是「SQL 文本正确但表/列不存在」（research D8） | 通过 |
| AGENTS.md | `docs/` 用简体中文；按明确路径暂存 | 全部 Spec 文档为简体中文；提交按文件路径逐个暂存 | 通过 |
| Overview 既有事实 | 草稿按 `material_states[]` 组织；λ/ωlog 属计算上下文、Tc 属 `tc_results` | 新数据段嵌套在材料状态之下，与已记录的数据归属一致（research D3） | 通过 |
| Spec 假设 | 无已批准论文、无结构模型记录 | SC-004 的非空结果在 Go 测试内构造已批准数据验证；结构相关只验空态，均已在 spec 假设中声明 | 通过 |

## Feature 文档结构

```text
docs/specs/57-paper-detail-data-parity/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── paper-detail.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
goserver/
├── models/models.go              # 删除 12 个 gorm:"-" 字段；补 SuperconductorProperty→PropertyDefinition 关联
├── handlers/papers.go            # GetPaper 补 Preload；materialStatesToDict 补字段并嵌套新数据段；
│                                 # keyPropertiesToDict 改真实来源；approvedRecordSearchQuery 改真实表；
│                                 # flatRecordToDict 改真实来源
├── handlers/admin.go             # keyPropertyUpdateFields 与 newKeyProperty 收敛为真实列
├── handlers/papers_test.go       # 新增真实插入测试
└── handlers/paper_detail_test.go # 新增（详情契约与搜索契约）

frontend/src/
├── components/ChartGroupEditor.tsx  # 压强/类型改读材料状态
├── pages/share.tsx                  # 移除主记录高亮；条件列改读材料状态
├── pages/AdminPage.tsx              # 物性 payload 收敛为真实列
└── components/PaperEditView.tsx     # 仅改字段来源（死代码清理属 #59）
```

**结构选择**：改动集中在读取侧的三个 Go 文件，写入侧（`backend/ingest/scientific_drafts.py`）完全不动，保证数据所有权不变。前端只改「读哪个字段」，不动组件划分与排版，为 #59 的展示重构留出空间；`PaperEditView` 因去留待 #59 决策而只做最小修正。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001 / US1 | `GetPaper` Preload `MaterialStates.TcResults`；`materialStatesToDict` 输出 `tc_results` | Go 测试真实插入 Tc 结果后断言返回；quickstart 场景 1 |
| FR-002 / US1 | `GetPaper` Preload `MaterialStates.CalculationContexts`；序列化 `calculation_contexts` | Go 测试断言 λ/μ*；quickstart 场景 1 |
| FR-003 / US1 | `materialStatesToDict` 补压强值/下限/上限/原文/原文单位 | Go 测试断言单臂区间；quickstart 场景 2 |
| FR-004 / US1 | `materialStatesToDict` 补空间群、温度、磁场、`state_kind`、`note` | Go 测试断言 `Fm-3m`/225；quickstart 场景 2 |
| FR-005 / US1 | `SuperconductorProperty` 补 `PropertyDefinition` 关联；`keyPropertiesToDict` 取 `DisplayName` 回退 `NameRaw` | Go 测试断言名称非空；quickstart 场景 3 |
| FR-006 / US2 | `models.go` 删除 12 个兼容字段；`keyPropertiesToDict` 同步收敛 | Go 测试断言响应键集合不含已删字段；编译期保证无残留 |
| FR-007 / US3 | `approvedRecordSearchQuery` 改 `tc_results` JOIN `material_states` JOIN `papers` | Go 测试真实查询不报错并返回行；quickstart 场景 4 |
| FR-008 / US3 | 筛选列按 research D5 映射表重映射；`flatRecordToDict` 改真实来源 | Go 测试对压强/类型筛选断言结果；quickstart 场景 4 |
| FR-009 / US3 | `keyPropertyUpdateFields`、`newKeyProperty` 收敛；`AdminPage.tsx` payload 同步 | Go 测试断言更新落库；quickstart 场景 5 |
| FR-010 / 全部 | 保留 `key_properties` 顶层键；前端消费方同步适配 | Go 全量测试 + 前端 Vitest 全量 + `tsc --noEmit` |

## 阶段与依赖

1. **基础能力（阻断全部故事）**：`models.go` 的字段删除与关联补齐。三个故事都依赖它——删除字段会使所有引用点编译失败，必须先完成模型再逐个修复引用点，否则无法编译、无法运行任何测试。
2. **用户故事 1（P1）**：详情接口补全数据段与材料状态字段。改 `GetPaper` 与 `materialStatesToDict`。
3. **用户故事 2（P1）**：`keyPropertiesToDict` 改真实来源并移除已删字段。与故事 1 同文件，需串行。
4. **用户故事 3（P1）**：记录搜索改真实表、管理员写入收敛、前端消费方适配。搜索与 admin 在不同文件可并行；前端四个文件互相独立可并行。
5. **收尾**：Go 与前端全量回归、镜像重建与部署、quickstart 人工验收、Overview 回写、关闭 Issue。

**关键顺序约束**：`models.go` 的字段删除一旦执行，`papers.go` 与 `admin.go` 的引用点立即编译失败。因此基础能力与前两个故事实际上是一次不可分割的编译单元——计划上按故事划分便于追踪验收，执行上必须连续完成到可编译状态再跑测试。这一点在 tasks.md 中以依赖关系明确标注。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 记录搜索的记录主体从 `key_properties` 改为 `tc_results` | Tc 已迁出普通物性表，而搜索结果每行的核心列就是 Tc；不换主体就无法在真实模型上表达「一行 = 一个材料在一组条件下的一个 Tc」 | 保留 `superconductor_properties` 为主体并按 `name_raw='critical_temperature'` 过滤：新模型下 Tc 根本不写入该表，过滤结果恒空，等于没修 |
| 三个故事共享一次编译单元 | 删除 `gorm:"-"` 字段会同时破坏详情、搜索、admin 三处的编译 | 保留字段只改详情页：FR-006 无法闭环，且留下搜索恒空与 admin 静默失效两个已知缺陷 |
