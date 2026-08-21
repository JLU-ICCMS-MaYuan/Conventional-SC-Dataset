# 图表统计 API 契约

## 端点

- `GET /api/papers/stats/tc-pressure?tc_field=<TcField>`
- `GET /api/papers/stats/tc-year?tc_field=<TcField>`
- `GET /api/papers/stats/chart-data?tc_field=<TcField>`：兼容别名，行为等同压力图。

## 输入

`tc_field` 可省略；省略或空字符串时使用 `experimental_tc`。非白名单值返回：

```json
{"error":"不支持的 Tc 字段"}
```

HTTP 状态为 400。

## 成功响应

保持数组响应。每个点至少包含：

```json
{
  "x": 200,
  "y": 250,
  "formula": "LaH10",
  "sc_type": "hydride",
  "type": "experimental",
  "paper_id": 42,
  "doi": "10.x/example",
  "year": 2019,
  "tc_field": "experimental_tc"
}
```

字段无数据时返回 HTTP 200 和空数组。接口保持公开，只返回已允许公开的数据。

## 缓存与兼容

缓存键为 `chart:approved:<chart>:<TcField>`。响应继续提供现有调用方使用的 `x`、`y`、`formula`、`sc_type`、`type`、`paper_id`，新增字段为向后兼容扩展。
