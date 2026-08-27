# 数据模型：论文详情读取契约

**Feature**：[spec.md](spec.md)

**日期**：2026-08-27

本文只描述**读取侧**的数据来源与归属，写入契约不在本 Feature 范围内，保持不变。

## 实体关系（读取视角）

```text
papers (1)
  └── material_states (N)          外键 paper_id + paper_revision
        ├── superconductor (1)     材料身份、化学式
        ├── material_family (0..1) 材料家族（规范中文名）
        ├── structure_family_links (N) 结构家族及主次标记
        ├── tc_results (N)         临界温度结果
        ├── calculation_contexts (N) 计算上下文（λ、μ*、ωlog）
        ├── structures (N)         结构模型（当前全库 0 条）
        └── properties (N)         普通物性
              └── property_definition (1) 规范名与规范单位
```

**关键事实**：`tc_results`、`calculation_contexts`、`structure_models`、`superconductor_properties` 的外键都是 `material_state_id`，因此读取契约把它们嵌套在材料状态之下（research D3），不在论文顶层平铺。

## 字段来源对照：材料状态

| 输出字段 | 数据来源 | 本 Feature 状态 |
|---|---|---|
| `id`、`material`、`material_family`、`structure_families` | 既有 | 不变 |
| `element_count`、`material_dimensionality`、`superconductor_kind`、`crystal_system` | 既有 | 不变 |
| `pressure_value_gpa` | `material_states.pressure_value_gpa` | 不变 |
| `pressure_min_gpa` | `material_states.pressure_min_gpa` | **新增** |
| `pressure_max_gpa` | `material_states.pressure_max_gpa` | **新增** |
| `pressure_raw` | `material_states.pressure_raw` | **新增** |
| `pressure_unit_raw` | `material_states.pressure_unit_raw` | **新增** |
| `reported_space_group_symbol` | `material_states.reported_space_group_symbol` | **新增** |
| `reported_space_group_number` | `material_states.reported_space_group_number` | **新增** |
| `temperature_value_k` | `material_states.temperature_value_k` | **新增** |
| `temperature_raw` | `material_states.temperature_raw` | **新增** |
| `magnetic_field_t` | `material_states.magnetic_field_t` | **新增** |
| `state_kind` | `material_states.state_kind` | **新增** |
| `note` | `material_states.note` | **新增** |
| `tc_results[]` | `tc_results` where `material_state_id` | **新增（嵌套）** |
| `calculation_contexts[]` | `calculation_contexts` where `material_state_id` | **新增（嵌套）** |

**压强语义约束**（沿用 #54，不改变）：`pressure_min_gpa` 与 `pressure_max_gpa` 允许单臂——只有一侧有值时另一侧为 NULL，不补造缺失边界；两侧都有值时要求 min≤max。读取侧必须原样透出 NULL，使消费方能区分「无上限」与「上限为 0」。

## 字段来源对照：物性

| 输出字段 | 修复前 | 修复后 |
|---|---|---|
| `id`、`paper_id`、`material` | 真实列（`material_raw`） | 不变 |
| `name` | `gorm:"-"` 恒空字符串 | `property_definitions.display_name`，回退 `name_raw` |
| `name_raw` | 真实列 | 不变 |
| `value_min`、`value_max`、`value_raw`、`unit` | 真实列（`unit` ← `unit_raw`） | 不变 |
| `value_number` | 真实列，此前未输出 | **新增输出** |
| `canonical_unit` | 真实列，此前未输出 | **新增输出** |
| `condition_note` | 真实列 | 不变 |
| `superconductor_id` | `gorm:"-"` 恒 null | **移除**（材料归属由所属材料状态表达） |
| `name_note` | `gorm:"-"` 恒 null | **移除**（无对应列） |
| `pressure_gpa` | `gorm:"-"` 恒 null | **移除**（条件上提到材料状态） |
| `temperature_k` | `gorm:"-"` 恒 null | **移除**（同上） |
| `condition_json` | `gorm:"-"` 恒 null | **移除**（`condition_note` 是真实列） |
| `is_primary` | `gorm:"-"` 恒 false | **移除**（物性无主次语义） |
| `superconductor_type` | `gorm:"-"` 恒 null | **移除**（由 `state_kind`/`result_kind` 表达） |
| `article_type` | `gorm:"-"` 恒 null | **移除**（无对应列） |
| `source_label` | `gorm:"-"` 恒空字符串 | **移除**（无对应列） |
| `structure_text` | `gorm:"-"` 恒 null | **移除**（改由 `structure_models` 提供） |
| `structure_format` | `gorm:"-"` 恒 null | **移除**（同上） |

**移除判据**：`superconductor_properties` 表实测列清单为 `id`、`paper_id`、`paper_revision`、`material_state_id`、`structure_id`、`calculation_context_id`、`property_definition_id`、`material_raw`、`name_raw`、`value_raw`、`unit_raw`、`value_number`、`value_min`、`value_max`、`canonical_unit`、`condition_note`、`source_fingerprint`、`created_at`、`updated_at`。上表所有「移除」项均不在此清单中。

## 新增输出：Tc 结果

来源 `tc_results`，字段 `result_kind`、`tc_method`、`tc_method_custom`、`tc_value_k`、`tc_min_k`、`tc_max_k`、`uncertainty_k`、`value_raw`、`unit_raw`、`source_locator`。

**归属约束**：Tc 只存在于本表，不在 `superconductor_properties` 中（Overview 已记录「Tc 属于 `tc_results`」）。因此任何以普通物性表查 Tc 的读取路径必然为空——这正是记录搜索失效的根因之一。

## 新增输出：计算上下文

来源 `calculation_contexts`，字段 `lambda_ep`、`mu_star`、`omega_log_k`、`electronic_method`、`exchange_correlation`、`pseudopotential_type`、`pseudopotential_name`、`spin_orbit_coupling`、`phonon_method`、`phonon_nuclear_treatment`、`epc_method`、`k_grid`、`q_grid`、`energy_cutoff_value`、`energy_cutoff_unit`、`calculation_code`、`missing_structure_reason`。

**归属约束**：λ 与 ωlog 只存在于本表（Overview 已记录）。允许同一材料状态有多条计算上下文——论文 4 即有 2 条，其中 1 条全为 NULL、另 1 条含 λ=2.56/μ*=0.1。读取侧全部返回，不做筛选或合并，避免读取侧擅自判定「哪条才算有效」。

## 记录搜索的记录主体变更

| 维度 | 修复前 | 修复后 |
|---|---|---|
| 主表 | `key_properties`（表不存在） | `tc_results` |
| JOIN | `papers` | `material_states`、`papers` |
| 记录语义 | 一条 Tc 物性行 | 一个材料在一组条件下的一个 Tc 结果 |
| Tc 取值 | `value_max` / `value_min` | `tc_value_k`（区间用 `tc_min_k`/`tc_max_k`） |
| 压强筛选 | `pressure_gpa`（列不存在） | `material_states.pressure_value_gpa` |
| 类型筛选 | `superconductor_type`（列不存在） | `material_states.state_kind` |
| 主记录筛选 | `is_primary`（列不存在） | 取消（新模型无此语义） |
| 元素筛选 | `superconductor_id`（列不存在） | `material_states.superconductor_id` |
| 空间群列 | 硬编码 `"-"` | `material_states.reported_space_group_symbol` |

记录语义在用户可见层面保持一致（一行仍是「某材料在某条件下的某个 Tc」），因此前端结果表结构无需改动。

## 管理员物性写入的字段收敛

| 字段 | 修复前 | 修复后 |
|---|---|---|
| `material`、`name_raw`、`value_raw`、`unit`、`value_min`、`value_max`、`condition_note` | 真实列 | 保留 |
| `value_number`、`canonical_unit` | 未支持 | **新增支持**（真实列） |
| `name`、`name_note`、`pressure_gpa`、`temperature_k`、`is_primary`、`article_type`、`condition_json`、`structure_text`、`structure_format` | 接受后静默丢弃 | **不再接受** |

**为何不转写**：把这些字段转写到材料状态，会让管理员通过物性接口间接修改材料状态的条件字段，绕过材料状态自身的校验与审核语义，属于悄悄改变数据所有权（research D6）。FR-009 因此要求「写入真实列或明确不接受」，二者之外没有第三种合法状态。

## 消费方影响核查

| 消费方 | 依赖的已移除字段 | 新来源 |
|---|---|---|
| `frontend/src/components/ChartGroupEditor.tsx:210-211`、`:467-468` | `pressure_gpa`、`superconductor_type` | 所属材料状态的 `pressure_value_gpa`、`state_kind` |
| `frontend/src/pages/share.tsx:588`、`:591`、`:597` | `is_primary`、`pressure_gpa`、`temperature_k` | 移除主次高亮；条件列读材料状态 |
| `frontend/src/pages/AdminPage.tsx:351` | 9 个无列字段 | payload 收敛为真实列 |
| `frontend/src/components/PaperEditView.tsx:127-133`、`:262-325` | `structure_text`、`name`、`pressure_gpa`、`temperature_k`、`is_primary` | 字段来源修正；组件去留由 #59 决策 |
| `goserver/handlers/papers.go:790-830` `flatRecordToDict` | `PressureGpa`、`SuperconductorType` | 材料状态对应字段 |
| `goserver/handlers/admin.go:265-283`、`:39-43` | 9 个无列字段 | 白名单收敛 |

核查方法：对 12 个字段逐个全仓库检索引用点（Go 与前端各一轮），确认上表已穷尽。
