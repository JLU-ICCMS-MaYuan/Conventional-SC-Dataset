# 数据模型：上传科学草稿

## 草稿实体

### `material_states[]`

| 字段 | 规则 |
|---|---|
| `material` | 必填、可解析化学式 |
| `pressure_value_gpa` | 可空非负单值 |
| `pressure_min_gpa/pressure_max_gpa` | 成对出现、非负且 min≤max |
| `pressure_raw/pressure_unit_raw` | 保留论文原文 |
| `state_kind` | theoretical/experimental/mixed/unknown |
| `reported_space_group_symbol` | 可空论文报告符号 |
| `reported_space_group_number` | 可空 1–230 |
| `structure` | 可空；存在时必须同时含 format/text |
| `calculation_context` | 可空；λ、ωlog、μ* 非负 |
| `experimental_context` | 可空；默认 Tc 判据 unknown |
| `tc_results[]` | Tc 单值或完整范围，含 theory/experiment 类型 |
| `properties[]` | 排除 Tc、λ、ωlog、空间群后的普通物性 |

状态按 `material + pressure + state_kind + reported_space_group（如有）` 区分；不同压力或不同报告空间群必须生成不同状态；无空间群时不得静默合并多个结构候选。

## 持久化映射

| 草稿 | 目标实体 |
|---|---|
| material | `ChemicalSystem → Superconductor` |
| 压力、报告空间群 | `MaterialState` |
| 完整结构文本 | `StructureModel` |
| λ、ωlog、μ* | `CalculationContext` |
| 实验判据 | `ExperimentalContext` |
| Tc | `TcResult` |
| 其他物性 | `PropertyDefinition → SuperconductorProperty` |
| 原文证据 | `PaperEvidence` 与现有三类结果连接表 |

## 生命周期

1. AI 新输出直接产生 `material_states`。
2. 当前 schema version 的旧草稿在 GET/PUT 边界一次性转换。
3. 用户保存后 Redis 仅存新契约。
4. 用户提交后同一事务创建 Paper 当前 revision 的文件、Evidence 和科学实体。
5. 任一约束失败时事务回滚，Redis 草稿保持可恢复。

## 数据库扩展

`material_states` 新增：

- `reported_space_group_symbol VARCHAR(100) NULL`
- `reported_space_group_number SMALLINT NULL`
- CHECK：群号为空或位于 1–230。

字段名包含 `reported_`，明确它来自论文声明，不等同于由 CIF/POSCAR 解析验证的
`structure_models.space_group_*`。
