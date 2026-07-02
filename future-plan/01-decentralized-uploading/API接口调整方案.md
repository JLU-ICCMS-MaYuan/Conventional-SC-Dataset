# 01 去中心化超导数据上传：API 接口调整方案

## 接口目标

API 需要支持论文、超导参数记录和晶体结构的一体化提交，同时保留审核、清洗和结构追溯能力。

## 规划接口

### 一体化上传接口

`POST /api/upload/superconductor-record`

用途：提交论文元数据、超导参数记录和结构引用。

核心字段：

- `doi`
- `chemical_formula`
- `pressure_gpa`
- `tc_value`
- `tc_method`
- `structure_format`
- `structure_text`
- `space_group_symbol`
- `space_group_number`
- `lambda_value`
- `omega_log`
- `n_ef_total`
- `source_type`

### 批量清洗预览接口

`POST /api/upload/preview`

用途：批量文件正式入库前返回清洗结果。

响应需要包含：

- 可入库记录
- 缺失字段记录
- 重复结构记录
- 冲突结构记录
- 需要人工确认记录

### 记录结构绑定接口

`GET /api/records/{record_id}/structure`

用途：按超导参数记录读取对应晶体结构。

## 兼容策略

现有 `POST /api/structures/`、`GET /api/structures/by-record/{record_id}` 和结构审核接口继续保留。新接口应先作为一体化入口，不应立即移除旧结构接口。

## 错误处理

- 400：字段缺失或结构解析失败。
- 401：未登录。
- 403：无上传权限。
- 409：同一材料、压强和空间群下存在冲突结构。

## 验收标准

- 接口能表达单条记录的压强、结构、Tc 和超导参数。
- 批量预览不会直接写入正式数据。
- 结构冲突必须显式返回给前端。
