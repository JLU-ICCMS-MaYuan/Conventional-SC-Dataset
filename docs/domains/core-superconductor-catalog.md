# 超导主目录

## 职责

主库以元素、化学体系、超导体、文献和超导记录组织可检索的超导数据。它是常规
检索、审核和图表指标的关系型事实来源，不与 RAG 的独立数据库混用。

## 核心模型

- `PeriodicTableElement` 保存周期表元素及原子序数、周期、族和分类。
- `ChemicalSystem` 用规范化 `system_key` 和元素列表表示元素体系。
- `Superconductor` 归属一个化学体系；`formula_normalized` 唯一。
- `Paper` 可由用户提交并由审核用户处理；状态默认是 `pending`。
- `SuperconductorRecord` 关联超导体和可选文献，保存压力、空间群、稳定性、Tc、
  计算参数及 `show_in_chart`。

## 约束

- 记录必须关联超导体，文献关联可以为空。
- 化学体系、超导体和文献均通过 ORM 关系表达，不以自由文本替代关联。
- 图表公开性由记录的 `show_in_chart` 决定，审核接口负责批量变更该标记。

## 证据

- `backend/models.py`
- `backend/api/papers.py`
- `backend/api/admin.py`

## 已知缺口

- 主库与 RAG 关系库使用不同连接配置；两者间的数据同步责任尚未形成权威设计，
  应建立 `type:doc-debt` Issue。
