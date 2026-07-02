# 03 超导数据检索与数据库发现当前规划

## 总体定位

负责元素周期表、化学式、本地数据库和外部数据库的统一发现。

## 当前状态

已落地，结果页表格待重构。

## 文档导航

- [总体规划](README.md)
- [前端设计](frontend-design.md)
- [后端设计](backend-design.md)
- [API 设计](api-design.md)

## 核心建设内容

### 前端

- `/elements` 负责元素选择，`/compound/{element_symbols}` 负责结果展示。
- 结果页改为记录级表格，固定列为体系名称、压强、超导类型、数据来源、审核状态、DOI。
- DOI 从原第三列调整到第六列，第三列只展示超导类型。

### 后端

- 检索结果应从论文聚合逐步转为记录级扁平数据，保留来源和审核状态。
- 本地数据、Alexandria 和 HTSC-2025 需要明确来源，不混同审核等级。
- La-H 检索应返回 LaH、LaH6、LaH4、LaH2、LaH3 等多条相关体系。

### API

- `POST /api/papers/search-by-mode`：当前主检索接口。
- `POST /api/papers/search/all`：三源合并发现。
- 未来新增记录级表格接口，返回 `formula`、`pressure_gpa`、`superconductor_type`、`source_type`、`review_status`、`doi`。

## 数据模型与数据流

数据来自 `superconductors`、`superconductor_records`、`papers` 及外部来源适配结果。前端展示必须保留本地/外部、实验/理论、已审核/未审核差异。

## 验收标准

- 表格六列顺序正确。
- DOI 位于第六列。
- 外部来源有明确标识。
