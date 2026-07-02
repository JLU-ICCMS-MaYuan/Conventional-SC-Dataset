# 04 超导发展知识图谱：API 接口调整方案

## 规划接口

- `GET /api/knowledge-graph/material/{formula}`：查询材料局部图。
- `POST /api/knowledge-graph/search`：按元素、Tc、压强、年份筛选关系。
- `GET /api/knowledge-graph/properties/{formula}`：查询材料属性集合。

## 响应结构

响应应包含：

- `nodes`
- `edges`
- `source_records`
- `source_papers`

## 验收标准

- 节点和边都能追溯到原始记录。
- 空图谱返回空数组和提示信息。
- API 不暴露未审核敏感数据。
