# 01 去中心化超导数据上传：API 接口调整方案

## 接口目标

API 设计必须服务最终合并表方案：一条 `superconductor_records` 就是一条完整的超导数据样本。接口不再围绕“参数表和结构表分开维护”设计，而是直接创建、预览、审核和读取完整记录。

后端结构相同判断必须依赖 StructurePrototypeAnalysisPackage，并且只在同一材料、同一压强下执行。不同压强天然视为不同结构样本，不调用结构相同判断，不合并、不去重。

依赖仓库：

`https://github.com/chuanxun/StructurePrototypeAnalysisPackage.git`

## 一体化记录预览接口

`POST /api/superconductor-records/preview`

用途：正式写入前预览一条完整超导数据样本的解析结果、字段完整性、结构解析结果和同压强结构比较结果。

### 请求字段

- `doi`
- `chemical_formula`
- `elements_list`
- `pressure_gpa`
- `space_group_symbol`
- `space_group_number`
- `tc_value`
- `tc_method`
- `lambda_value`
- `omega_log`
- `n_ef_total`
- `calculation_code`
- `method`
- `structure_format`
- `structure_text`
- `structure_fingerprint`
- `structure_source_type`
- `structure_source_label`

### 响应字段

- `can_submit`
- `normalized_record`
- `structure_preview`
- `missing_fields`
- `validation_errors`
- `same_pressure_structure_check`
- `review_status`

### `structure_preview`

结构预览应包含：

- `structure_format`
- `atom_count`
- `structure_elements_list`
- `cell_parameters`
- `volume`
- `space_group_symbol`
- `space_group_number`

### `same_pressure_structure_check`

只比较同一材料、同一压强下的结构。

返回值建议包括：

- `check_scope`：固定说明为同一材料、同一压强。
- `tool`：`StructurePrototypeAnalysisPackage`
- `result`：`same`、`different`、`uncertain`、`not_checked`
- `matched_record_ids`
- `message`

不同压强时返回 `not_checked`，并说明“不同压强天然视为不同结构样本”。

## 一体化记录创建接口

`POST /api/superconductor-records`

用途：创建一条完整 `superconductor_records`。该接口直接写入参数字段和结构字段，不再创建独立结构表记录。

### 请求字段

字段与预览接口保持一致。提交前前端应先调用预览接口。

### 响应字段

- `id`
- `chemical_formula`
- `pressure_gpa`
- `tc_value`
- `structure_format`
- `structure_source_type`
- `structure_source_label`
- `review_status`
- `created_at`

创建后的默认 `review_status` 为 `pending`。只有参数数据和晶体结构数据都通过审核后，整条记录才可以变为 `approved`。

## 同压强结构比较接口

`POST /api/superconductor-records/compare-structure`

用途：单独比较新上传结构与同一材料、同一压强下已有结构是否相同。

### 请求字段

- `chemical_formula`
- `pressure_gpa`
- `structure_format`
- `structure_text`
- `space_group_symbol`
- `space_group_number`

### 处理规则

- 只查询同一材料、同一压强下的已有记录。
- 调用 StructurePrototypeAnalysisPackage 比较结构。
- 如果材料相同但压强不同，不执行比较，返回 `not_checked`。
- 不能用 `structure_fingerprint`、坐标四舍五入或文本 hash 作为结构相同判断依据。

### 响应字段

- `result`：`same`、`different`、`uncertain`、`not_checked`
- `matched_record_ids`
- `conflict_record_ids`
- `message`
- `tool`

## 批量清洗预览接口

`POST /api/superconductor-records/batch-preview`

用途：批量文件正式入库前返回清洗、解析、缺失字段和结构冲突结果。该接口不写入正式数据。

响应需要分组返回：

- `ready_items`
- `missing_pressure_items`
- `missing_tc_items`
- `missing_structure_items`
- `structure_parse_failed_items`
- `same_pressure_duplicate_items`
- `same_pressure_conflict_items`
- `manual_review_items`

每个数据项至少包含：

- `row_index`
- `chemical_formula`
- `pressure_gpa`
- `tc_value`
- `doi`
- `structure_format`
- `structure_source_type`
- `structure_source_label`
- `issues`

## 单条记录详情接口

`GET /api/superconductor-records/{record_id}`

用途：读取单条完整超导数据样本，包括参数字段和结构字段。该接口只读取 `superconductor_records` 内部已经合并后的结构信息。

响应应包含：

- 基础材料字段
- 压强
- Tc
- 超导参数
- 晶体结构字段
- 结构来源字段
- `review_status`
- 审核备注

## 统一审核状态

`review_status` 是整条记录的唯一审核状态。

| 状态 | 含义 |
| --- | --- |
| `pending` | 参数数据或结构数据仍待审核。 |
| `approved` | 参数数据和结构数据都已通过审核。 |
| `rejected` | 参数数据或结构数据中任一关键部分被拒绝。 |

API 不再提供单独的 `structure_review_status` 作为正式业务状态。

## 错误处理

- 400：字段缺失、单位不合法、结构文件无法解析。
- 401：未登录。
- 403：无上传或审核权限。
- 404：目标记录不存在。
- 409：同一材料、同一压强下存在结构冲突，或 StructurePrototypeAnalysisPackage 无法稳定判定。

## 验收标准

- API 能表达一条完整 `superconductor_records` 样本。
- API 文档不再把结构读取描述为跨表关系接口。
- 同一压强才调用 StructurePrototypeAnalysisPackage。
- 不同压强返回 `not_checked`，并视为不同结构样本。
- 批量预览接口只返回清洗和冲突结果，不写入正式数据。
- `structure_source_type`、`structure_source_label`、`review_status` 与后端规划文档一致。
