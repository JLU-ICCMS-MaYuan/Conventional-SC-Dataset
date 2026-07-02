# 03 超导数据检索与数据库发现：API 接口调整方案

## 规划接口

### 记录级检索接口

`POST /api/search/superconductor-records`

用途：返回结果页表格直接使用的数据行。

请求字段：

- `mode`
- `elements`
- `formula`
- `limit`
- `offset`

响应字段：

- `formula`
- `pressure_gpa`
- `superconductor_type`
- `source_type`
- `review_status`
- `doi`
- `source_system`

## 兼容策略

现有 `POST /api/papers/search-by-mode` 和 `POST /api/papers/search/all` 暂时保留。新接口优先服务新表格，不直接破坏旧结果页。

## 验收标准

- API 返回字段顺序和前端表格语义一致。
- DOI 字段独立返回，不嵌入标题或摘要。
- 外部来源返回 `source_system`。
