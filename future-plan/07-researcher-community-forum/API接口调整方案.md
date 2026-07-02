# 07 研究者社区与图表论坛：API 接口调整方案

## 默认图表接口

继续保留：

- `GET /api/papers/stats/tc-pressure`
- `GET /api/papers/stats/tc-year`
- `GET /api/papers/stats/chart-data`

## 规划新增接口

### 读取个人图表配置

`GET /api/users/me/chart-settings`

### 保存个人图表配置

`PUT /api/users/me/chart-settings`

请求字段：

- `chart_type`
- `hidden_record_ids`
- `added_record_ids`

### 搜索可添加数据点

`GET /api/chart-points/search`

### 导出个人图表数据

`GET /api/users/me/chart-export`

导出字段顺序固定为：

1. 压强
2. 年代
3. Formula
4. Tc
5. DOI

## 验收标准

- 访客不能保存个人图表配置。
- 导出字段顺序严格固定。
- 保存配置不会改变默认图表数据。
