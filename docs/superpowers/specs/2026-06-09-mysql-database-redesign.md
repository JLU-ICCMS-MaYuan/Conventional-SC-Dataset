# MySQL 数据库重设计方案

日期：2026-06-09

## 目标

本设计用于把现有超导数据库从 SQLite 迁移到 MySQL，并重新整理数据结构。新结构不再保存图片，不再把不同数据库作为搜索入口，而是以超导体系和化学式作为主要查询入口。

核心目标：

- 使用 MySQL 作为唯一正式运行数据库，SQLite 只作为旧数据来源或历史参考。
- 公开查询页面显示所有数据，不按审核状态过滤。
- 用户先搜索元素体系或化学式，再查看对应超导体和所有来源的数据。
- 数据来源通过 `paper_id` 和 `source_label` 表示，不单独建立 `data_sources` 表。
- `show_in_chart` 放在具体数据记录上，用于控制该记录是否进入 Tc-Pressure 和 Tc-Year 散点图。

## 查询理念

网站查询入口不是论文，也不是某个独立数据库，而是：

```text
chemical_system -> superconductor -> superconductor_records
```

例如用户搜索 `La-H`：

```text
La-H
  -> LaH10
  -> LaH6
  -> LaH3
```

点进 `LaH10` 后，页面显示该化合物的全部数据来源：

```text
LaH10 | 200 GPa | Fm-3m | paper
LaH10 | 120 GPa | Fm-3m | Alexandria
LaH10 | 150 GPa | C2/m  | HTSC-2025
```

旧页面里的“数据库”下拉框应删除。数据库来源不再作为搜索起点，只作为结果中的 `source_label` 展示或后续筛选条件。

## 搜索方式

搜索模式改名为：

```text
formula_search
elements_exact_search
elements_combination_search
elements_contained_search
```

含义：

- `formula_search`：输入化学式，精确搜索具体超导体，例如 `LaH10`。
- `elements_exact_search`：输入元素体系，只搜索完全相同元素集合，例如 `La-H` 只返回 `H-La` 体系下的超导体。
- `elements_combination_search`：输入多个元素，搜索输入元素集合的子组合体系，例如 `La-H-S` 可以返回 `H-La`、`H-S`、`H-La-S`。
- `elements_contained_search`：输入元素，搜索所有包含这些元素的体系，例如 `La-H` 可以返回 `H-La`、`H-La-S`、`H-La-O`。

旧名称映射：

```text
precision   -> formula_search
only        -> elements_exact_search
combination -> elements_combination_search
contain     -> elements_contained_search
```

## 表结构总览

最终设计包含 6 张表：

```text
periodic_table_elements
chemical_systems
superconductors
papers
users
superconductor_records
```

不再设计：

```text
paper_images
paper_authors
chemical_system_elements
superconductor_elements
data_sources
element_resolved_dos
```

这些信息分别被合并到 `papers`、`chemical_systems`、`superconductors` 和 `superconductor_records` 中。

## periodic_table_elements

用途：保存周期表元素基础信息。它是字典表，不保存论文数据或超导数据。

字段：

```text
id
atomic_number
symbol
english_name
chinese_name
atomic_mass
period_number
group_number
category
created_at
updated_at
```

设计理由：

- `symbol` 用于和体系、化学式、元素贡献数据关联。
- 元素信息只维护一份，避免在业务数据中重复写周期表信息。

## chemical_systems

用途：保存元素体系，例如 `H-La`、`H-S`、`Ba-Cu-O-Y`。

字段：

```text
id
system_key
elements_list
element_count
created_at
updated_at
```

约束和规则：

- `system_key` 唯一。
- `system_key` 内部按元素符号字母排序。
- 用户输入 `La-H` 时，系统存储和查询为 `H-La`。
- `elements_list` 使用 JSON，例如 `["H", "La"]`。

设计理由：

- `chemical_systems` 是用户按元素体系搜索的入口。
- 不再单独建立 `chemical_system_elements`，因为体系表只承担轻量搜索入口职责。

## superconductors

用途：保存具体超导体或化合物，例如 `LaH10`、`LaH6`、`H3S`。

字段：

```text
id
chemical_system_id
chemical_formula
formula_normalized
display_name
elements_list
composition
element_ratio
created_at
updated_at
```

约束和规则：

- `chemical_system_id` 指向 `chemical_systems.id`。
- `formula_normalized` 唯一。
- `formula_normalized` 按元素符号字母排序生成，例如 `LaH10` 标准化为 `H10La`。
- `elements_list` 使用 JSON，例如 `["H", "La"]`。
- `composition` 使用 JSON，例如 `{"La": 1, "H": 10}`。
- `element_ratio` 使用 JSON，例如 `{"La": 0.0909, "H": 0.9091}`。

设计理由：

- `superconductors` 是页面聚合对象。搜索 `H-La` 后，先展示 `LaH10`、`LaH6` 等化合物。
- 不和 `superconductor_records` 合并，避免每条压力点数据重复保存化学式和组成信息。
- 不再单独建立 `superconductor_elements`，因为目前不提供复杂元素比例检索。

## papers

用途：保存论文元信息、作者信息、上传审核信息。

字段：

```text
id
doi
title
journal
volume
pages
year
abstract
authors
uploaded_by_user_id
reviewed_by_user_id
review_status
reviewed_at
review_comment
created_at
updated_at
```

约束和规则：

- `doi` 唯一。
- `review_status` 默认 `pending`。
- `review_status` 可选值为 `pending`、`approved`、`rejected`、`needs_revision`。
- `authors` 使用 JSON，保留作者顺序和单位，不做作者身份去重。

`authors` 示例：

```json
[
  {
    "name": "A. Smith",
    "affiliation": "University A"
  },
  {
    "name": "B. Wang",
    "affiliation": null
  }
]
```

设计理由：

- 作者同名不代表同一个人，因此不建立全局 `authors` 表。
- 网站不提供按作者和单位检索，因此作者 JSON 足够。
- 上传者和审核者记录在论文层面，一篇论文作为整体提交和审核。
- 公开页面不按 `review_status` 过滤，审核状态只用于管理和标记数据可信度。

## users

用途：保存网站用户、管理员和超级管理员。

字段：

```text
id
email
password_hash
real_name
affiliation
role
is_approved
is_email_verified
created_at
updated_at
```

约束和规则：

- `email` 唯一。
- `role` 默认 `user`。
- `role` 可选值为 `user`、`admin`、`superadmin`。
- `is_approved` 默认 `false`。
- `is_email_verified` 默认 `false`。

设计理由：

- 使用单个 `role` 字段替代旧设计中的 `is_admin` 和 `is_superadmin` 两个布尔值。
- 用户是网站账户，不等于论文作者。论文作者保存在 `papers.authors` 中。

## superconductor_records

用途：保存某个超导体在某个压力、空间群、计算设置下的具体稳定性和超导性质。

### 归属和来源

字段：

```text
id
superconductor_id
paper_id
source_label
```

规则：

- `superconductor_id` 指向 `superconductors.id`。
- `paper_id` 可为空。来自论文时指向 `papers.id`；来自数据库或人工整理时为空。
- `source_label` 是人工指定的自由文本，例如 `paper`、`Alexandria`、`HTSC-2025`、`AI筛选数据库`、`人工整理`。

展示规则：

- 如果 `paper_id` 有值，前端可通过 `papers.doi` 生成 DOI 超链接。
- 如果 `paper_id` 为空，前端直接显示 `source_label`。

### 结构和压力

字段：

```text
pressure_gpa
space_group_symbol
space_group_number
crystal_structure
```

规则：

- `pressure_gpa` 单位为 GPa，只存明确单个数值。
- `space_group_symbol` 示例：`Fm-3m`、`C2/m`、`P6_3/mmc`。
- `space_group_number` 示例：225、12、194。

### 稳定性

字段：

```text
thermodynamically_stable
dynamically_stable
energy_above_hull
```

规则：

- `thermodynamically_stable` 为 `true`、`false` 或 `null`。
- `dynamically_stable` 为 `true`、`false` 或 `null`。
- `energy_above_hull` 单位固定为 `meV/atom`。

### Tc

字段：

```text
mcmillan_tc
allen_dynes_tc
isotropic_eliashberg_tc
anisotropic_eliashberg_tc
experimental_tc
```

规则：

- 所有 Tc 字段单位为 K。
- 一条记录代表同一 `superconductor + pressure_gpa + space_group` 下的一组结果。
- 不把 McMillan、Allen-Dynes、Eliashberg 拆成多行，而是在同一行用不同字段保存。

### 电声和电子参数

字段：

```text
lambda_value
omega_log
n_ef_total
element_n_ef
```

规则：

- `lambda_value` 无量纲。
- `omega_log` 单位为 K。
- `n_ef_total` 单位为 `states/eV/f.u.`。
- `element_n_ef` 使用 JSON，单位同 `n_ef_total`。

`element_n_ef` 示例：

```json
{
  "La": 0.2,
  "H": 1.8
}
```

### 赝势和计算设置

字段：

```text
pseudopotential_type
pseudopotential_name
exchange_correlation_functional
calculation_code
k_grid
q_grid
energy_cutoff_value
energy_cutoff_unit
```

示例：

```text
pseudopotential_type = PAW
pseudopotential_name = La.pbe-spfn-kjpaw_psl.1.0.0.UPF
exchange_correlation_functional = PBE
calculation_code = Quantum ESPRESSO
k_grid = 16x16x16
q_grid = 4x4x4
energy_cutoff_value = 80
energy_cutoff_unit = Ry
```

设计理由：

- 赝势、泛函、软件和网格会影响稳定性、声子、电子态密度和 Tc，必须跟具体记录绑定。

### 图表、方法和备注

字段：

```text
show_in_chart
s_factor
method
note
created_at
updated_at
```

规则：

- `show_in_chart` 默认 `false`。
- `show_in_chart = true` 时，该记录可进入 Tc-Pressure 和 Tc-Year 散点图。
- Tc-Year 图只使用有 `paper_id` 的记录，年份来自 `papers.year`。
- 来自数据库且 `paper_id` 为空的记录不进入 Tc-Year 图，但可以进入 Tc-Pressure 图。

## 页面和数据流

搜索页面：

1. 用户选择搜索方式。
2. 用户输入元素体系或化学式。
3. 后端查询 `chemical_systems` 或 `superconductors`。
4. 前端按 `superconductors` 聚合展示。

超导体详情页：

1. 用户点进某个 `superconductor`。
2. 后端查询该 `superconductor_id` 下所有 `superconductor_records`。
3. 如果记录有 `paper_id`，同时读取 `papers` 用于展示 DOI、标题和年份。
4. 如果记录没有 `paper_id`，直接展示 `source_label`。

图表：

1. Tc-Pressure 图读取 `superconductor_records.show_in_chart = true` 的记录。
2. Tc-Year 图读取 `show_in_chart = true` 且 `paper_id` 不为空的记录，年份来自 `papers.year`。

## MySQL 和迁移建议

新系统使用 MySQL 作为正式数据库。SQLite 不再作为运行数据库，只作为旧数据参考或重新导入来源。

建议引入 Alembic 管理表结构版本，不再依赖 `create_all + ALTER TABLE`。原因：

- 每次 schema 变化都有版本记录。
- 可以明确知道生产数据库当前处于哪个版本。
- 多人开发时不容易漏字段。
- 后续新增字段、索引、约束时更安全。

## 后续实现顺序

建议实现顺序：

1. 建立 MySQL 配置和 SQLAlchemy model。
2. 引入 Alembic 并生成初始迁移。
3. 实现 6 张表。
4. 改写搜索 API：`formula_search`、`elements_exact_search`、`elements_combination_search`、`elements_contained_search`。
5. 改写上传和审核流程。
6. 移除图片相关代码和数据库选择下拉框。
7. 重做 Tc-Pressure 和 Tc-Year 图表数据接口。

## 已确认约束

- 不保存图片。
- 不再支持 `paper_images`。
- 不提供按作者名和单位检索。
- 公开查询页面显示所有数据，包括 `pending`、`approved`、`rejected`、`needs_revision`。
- `show_in_chart` 控制图表展示，不控制公开查询。
- `source_label` 是人工指定的自由文本。
- `energy_above_hull` 单位固定为 `meV/atom`。
- Tc 单位固定为 K。
- `n_ef_total` 和 `element_n_ef` 单位为 `states/eV/f.u.`。
