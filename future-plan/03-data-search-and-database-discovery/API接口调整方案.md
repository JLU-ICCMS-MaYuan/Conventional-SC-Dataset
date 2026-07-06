# 03 超导数据检索与数据库发现：API 接口调整方案

## 接口目标

API 需要支持结果列表、右侧详情卡片和未来独立详情页。

第一阶段拆成两个主要接口：

1. 列表检索接口：返回分页摘要数据，用于表格展示、筛选和排序。
2. 详情接口：根据 `source_system + source_record_id` 返回完整详情，用于右侧详情卡片和独立详情页。

列表接口不返回完整详情，避免响应过重。

## 列表检索接口

`POST /api/search/superconductor-records`

用途：返回 `/compound/:elementSymbols` 结果页表格直接使用的分页摘要行。

### 请求字段

- `mode`：检索模式。
- `elements`：元素符号列表。
- `formula`：Formula 模糊搜索。
- `source_scope`：数据来源范围，默认 `local`。
- `tc_min`：代表 Tc 最小值。
- `tc_max`：代表 Tc 最大值。
- `pressure_min`：压强最小值。
- `pressure_max`：压强最大值。
- `year_min`：年份最小值。
- `year_max`：年份最大值。
- `superconductor_type`：超导类型。
- `space_group_number`：空间群编号。
- `space_group_min`：空间群编号范围最小值。
- `space_group_max`：空间群编号范围最大值。
- `review_status`：审核状态。
- `keyword`：DOI / 标题 / 关键词。
- `show_in_chart`：是否进入默认图表。
- `sort_by`：排序字段，默认 `representative_tc`。
- `sort_order`：排序顺序，默认 `desc`。
- `limit`
- `offset`

`source_scope` 取值：

- `local`
- `alexandria`
- `htsc2025`
- `all`

空间群筛选只接收 `space_group_number` 或 `space_group_min` / `space_group_max`，不提供空间群字符串筛选。

`keyword` 是接口兼容字段，但 03 静态 demo 的第二层筛选不展示 DOI / 标题 / 关键词筛选。

### 响应字段

响应为分页结构：

- `items`
- `total`
- `limit`
- `offset`
- `has_next`

`items` 每项包含：

- `source_system`
- `source_record_id`
- `year`
- `formula`
- `superconductor_type`
- `pressure_gpa`
- `representative_tc`
- `representative_tc_field`
- `representative_tc_label`
- `space_group_number`
- `data_source`
- `review_status`
- `doi`
- `show_in_chart`

这些字段对应前端表格 9 列，并额外提供定位详情所需的 `source_system` 和 `source_record_id`。

## 详情接口

`GET /api/search/superconductor-records/{source_system}/{source_record_id}`

用途：读取单条记录详情，供右侧详情卡片和未来独立详情页使用。

### 路径参数

- `source_system`：`local`、`alexandria`、`htsc2025`
- `source_record_id`：来源系统内的记录 ID

### 本地详情响应

本地记录的 `source_record_id` 指向 `superconductor_records.id`。

响应字段建议包含：

- `source_system`
- `source_record_id`
- `formula`
- `year`
- `doi`
- `paper_title`
- `journal`
- `review_status`
- `data_source`
- `all_tc_values`
- `representative_tc`
- `representative_tc_field`
- `representative_tc_label`
- `lambda_value`
- `omega_log`
- `n_ef_total`
- `s_factor`
- `pressure_gpa`
- `space_group_number`
- `space_group_symbol`
- `crystal_structure`
- `cell_parameters`
- `volume`
- `calculation_code`
- `method`
- `pseudopotential_type`
- `pseudopotential_name`
- `exchange_correlation_functional`
- `k_grid`
- `q_grid`
- `energy_cutoff_value`
- `energy_cutoff_unit`
- `source_label`
- `note`

`all_tc_values` 包含所有非空 Tc 字段：

- `experimental_tc`
- `anisotropic_eliashberg_tc`
- `isotropic_eliashberg_tc`
- `allen_dynes_tc`
- `mcmillan_tc`

### 外部详情响应

Alexandria 和 HTSC-2025 使用同一详情接口，但只返回该来源能提供的字段。

响应中必须包含：

- `source_system`
- `source_record_id`
- `formula`
- `data_source`
- `review_status`
- `external_source_note`

缺失字段返回空值或“未提供”。外部来源不能伪造本地 DOI、审核状态或计算参数。

## 独立详情页路由规划

前端未来规划统一详情页路由：

`/records/:sourceSystem/:sourceRecordId`

该页面复用详情接口。

示例：

- `/records/local/123`
- `/records/alexandria/mp-xxxx`
- `/records/htsc2025/456`

本轮只在 future-plan 中规划，不新增真实前端路由。

## 代表 Tc 字段语义

列表和详情接口都需要返回代表 Tc 相关字段：

- `representative_tc`
- `representative_tc_field`
- `representative_tc_label`

默认代表 Tc 规则：

1. `experimental_tc`
2. `anisotropic_eliashberg_tc`
3. `isotropic_eliashberg_tc`
4. `allen_dynes_tc`
5. `mcmillan_tc`

03 检索页只展示代表 Tc，不允许用户修改 Tc 类型。

## 兼容策略

现有接口暂时保留：

- `POST /api/papers/search-by-mode`
- `POST /api/papers/search/all`

新接口优先服务新版结果页，不直接破坏旧结果页。

## 错误处理

- 400：检索模式、来源范围、排序字段或筛选参数不合法。
- 404：目标 `source_system + source_record_id` 不存在。
- 422：空间群传入字符串而不是编号等参数语义错误。

## 验收标准

- 列表接口默认 `source_scope = local`。
- 列表接口默认按代表 Tc 降序。
- 列表接口响应字段能支撑 9 列表格展示。
- 列表接口支持 Formula、代表 Tc、压强、年份、超导类型、空间群编号或空间群编号范围、数据来源、审核状态、DOI / 关键词、`show_in_chart` 筛选。
- 详情接口支持 `local`、`alexandria`、`htsc2025`。
- 本地详情返回全部 Tc 字段、超导参数、结构信息、计算信息和论文信息。
- 外部详情缺失字段不伪造。
- 独立详情页规划使用 `/records/:sourceSystem/:sourceRecordId`。
