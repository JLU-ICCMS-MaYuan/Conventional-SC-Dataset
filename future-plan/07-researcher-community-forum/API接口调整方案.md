# 07 研究者社区与图表论坛：API 接口调整方案

## 接口目标

API 需要同时服务默认公共图表和注册用户个人图表。

默认公共图表继续使用现有接口。新增接口只处理个人配置、个人图表数据、候选点搜索和 CSV 导出。所有个人图表接口都必须基于本地 `superconductor_records` 的 `record_id`，不保存孤立散点坐标。

## 默认图表接口

继续保留：

- `GET /api/papers/stats/tc-pressure`
- `GET /api/papers/stats/tc-year`
- `GET /api/papers/stats/chart-data`

默认图表接口继续返回公共图表数据，不叠加个人配置。

## 图表类型

所有个人图表接口都需要支持 `chart_type`：

| 取值 | 含义 |
| --- | --- |
| `tc_pressure` | Tc-pressure 图表 |
| `tc_year` | Tc-year 图表 |

Tc-pressure 和 Tc-year 的个人配置必须分开保存、分开读取、分开导出。

## Tc 字段白名单

API 接收的 `tc_field` 只能是以下字段之一：

- `experimental_tc`
- `anisotropic_eliashberg_tc`
- `isotropic_eliashberg_tc`
- `allen_dynes_tc`
- `mcmillan_tc`

保存配置时，后端必须校验目标记录中对应 Tc 字段非空。

## 读取个人图表配置

`GET /api/users/me/chart-settings`

用途：读取当前登录用户在指定图表类型下的个人配置。

请求参数：

- `chart_type`

响应字段：

- `chart_type`
- `hidden_record_ids`
- `added_points`
- `tc_overrides`
- `updated_at`

`added_points` 每项包含：

- `record_id`
- `tc_field`

`tc_overrides` 每项包含：

- `record_id`
- `tc_field`

如果用户从未配置过该图表，返回空配置。

## 保存个人图表配置

`PUT /api/users/me/chart-settings`

用途：保存当前登录用户在指定图表类型下的个人配置。前端隐藏点、添加点、修改 Tc 类型或恢复默认后，都通过该接口自动保存。

请求字段：

- `chart_type`
- `hidden_record_ids`
- `added_points`
- `tc_overrides`

处理规则：

- 只能保存当前用户自己的配置。
- `record_id` 必须存在于本地 `superconductor_records`。
- `tc_field` 必须在白名单中。
- `tc_field` 对应的 Tc 值必须非空。
- 同一 `record_id` 重复出现时，以最后一次配置为准。
- 如果同一 `record_id` 同时出现在隐藏列表和添加列表中，隐藏优先。

响应字段：

- `chart_type`
- `saved`
- `updated_at`

## 读取个人图表数据

`GET /api/users/me/chart-data`

用途：返回当前用户、当前图表类型的最终个人图表点。该接口需要先读取默认公共图表，再叠加用户个人配置。

请求参数：

- `chart_type`

响应字段：

- `record_id`
- `formula`
- `pressure_gpa`
- `year`
- `tc_value`
- `tc_field`
- `available_tc_values`
- `doi`
- `review_status`
- `source_label`
- `superconductor_type`
- `point_origin`

`available_tc_values` 返回该记录所有非空 Tc 字段和值，供右侧抽屉和搜索结果展开使用。

`point_origin` 建议取值：

- `default`：来自公共默认图表。
- `added`：用户额外添加。
- `overridden`：默认点但用户覆盖了 Tc 类型。

## 搜索可添加图表点

`GET /api/chart-points/search`

用途：在当前图表下搜索本地数据库中可添加的数据点。该接口只搜索本地 `superconductor_records`，不搜索 Alexandria，不搜索 HTSC-2025。

请求参数：

- `chart_type`
- `formula`
- `doi`
- `year_min`
- `year_max`
- `pressure_min`
- `pressure_max`
- `tc_min`
- `tc_max`
- `review_status`
- `limit`
- `offset`

处理规则：

- `tc_pressure` 只返回有压强且至少有一个可用 Tc 字段的记录。
- `tc_year` 只返回有年份且至少有一个可用 Tc 字段的记录。
- Formula 支持模糊搜索。
- DOI 支持完整或部分匹配。
- 审核状态可筛选 `approved`、`pending`、`rejected`。
- 返回结果中必须包含全部非空 Tc 字段和值。

响应字段：

- `items`
- `total`
- `limit`
- `offset`

`items` 每项包含：

- `record_id`
- `formula`
- `pressure_gpa`
- `year`
- `default_tc_value`
- `default_tc_field`
- `available_tc_values`
- `doi`
- `review_status`
- `source_label`
- `superconductor_type`
- `already_in_chart`

如果 `already_in_chart = true`，前端再次添加时应覆盖该点的 Tc 类型，而不是生成重复点。

## 恢复默认图表

`POST /api/users/me/chart-settings/reset`

用途：清空当前用户、当前图表类型下的个人配置，使该图恢复默认公共图表。

请求字段：

- `chart_type`

处理规则：

- 只清空当前图表类型。
- 不影响另一张图。
- 不修改默认公共图表。
- 不修改 `superconductor_records`。
- 不修改 `show_in_chart`。

响应字段：

- `chart_type`
- `reset`
- `updated_at`

## 导出个人图表 CSV

`GET /api/users/me/chart-export.csv`

用途：导出当前用户、当前图表类型的最终个人图表数据。导出前必须应用个人配置合并规则，确保 CSV 与页面当前图表一致。

请求参数：

- `chart_type`

CSV 字段顺序固定为：

1. 压强
2. 年代
3. Formula
4. Tc
5. DOI
6. 审核状态
7. Tc 类型

导出规则：

- Tc 使用用户选择后的 `tc_field` 对应值。
- Tc-pressure 中缺少年代时，年代列留空。
- Tc-year 中缺少压强时，压强列留空。
- `pending` 和 `rejected` 必须在审核状态列保留，不能导出时丢失。

## 导出图片

图表图片导出建议由前端基于当前 Chart.js canvas 完成，不必新增后端图片导出接口。

如果后续需要服务端图片导出，再单独设计接口，不放入第一阶段。

## 错误处理

- 400：`chart_type` 不合法、`tc_field` 不合法、目标记录缺少当前图表所需字段。
- 401：未登录，不能读取或保存个人图表配置。
- 403：试图访问其他用户配置。
- 404：目标 `record_id` 不存在。
- 409：配置冲突，例如同一记录的 Tc 字段为空或已不再满足当前图表类型。

## 验收标准

- 默认公共图表接口不叠加个人配置。
- 所有个人图表接口都按 `chart_type` 区分 Tc-pressure 和 Tc-year。
- 保存配置支持 `hidden_record_ids`、`added_points`、`tc_overrides`。
- 搜索接口只返回本地 `superconductor_records`。
- 搜索结果包含全部可用 Tc 字段和值。
- 用户重复添加同一 `record_id` 时覆盖 Tc 类型，不生成重复点。
- 恢复默认只清空当前图表的个人配置。
- CSV 导出严格包含 7 列：压强、年代、Formula、Tc、DOI、审核状态、Tc 类型。
- 图片导出由前端处理，不额外引入后端图片生成复杂度。
