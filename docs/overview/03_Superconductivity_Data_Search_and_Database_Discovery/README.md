# 超导数据搜索与数据库发现

## 功能边界

该功能负责从元素组合、化学式和超导体记录出发查询本地论文与物性数据，补充 Alexandria、HTSC-2025 等外部候选材料，并提供结果分享导出、代表结构查询下载和 Tc 统计图表。当前前端入口是 `/search` 与 `/share`。它不负责修改权威数据、审核论文或摄入 RAG 文档。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [本地材料检索](local-material-search.md) | 按化学式或元素关系检索临界温度物性记录 | Go API、MySQL、`key_properties` |
| [外部数据集检索](external-dataset-search.md) | 查询 Alexandria 和 HTSC-2025 候选材料 | Go API、外部数据表 |
| [论文与物性结果](paper-and-property-results.md) | 组织论文、关键物性、结构预览和多源搜索结果 | 本地材料检索、论文关系 |
| [分享与导出](share-and-export.md) | 输出 JSON、RIS 等分享数据 | 论文与物性结果 |
| [代表结构查询与下载](representative-query-and-download.md) | 匹配超导记录、选取代表结构并控制下载 | 已批准结构、访问权限 |
| [Tc 历史与压力图表](tc-history-and-pressure-charts.md) | 生成并展示 Tc-year 和 P-Tc 数据及图表组合 | `key_properties`、Recharts、图表组合表 |

## 功能组成

```text
超导数据搜索与数据库发现
├── 本地材料检索
├── 外部数据集检索
├── 论文与物性结果
├── 分享与导出
├── 代表结构查询与下载
└── Tc 历史与压力图表
```

## 关联关系

用户从 `/search` 的周期表或化学式输入进入检索。本地模式经 Go API 查询 `chemical_systems`、`superconductors`、`key_properties` 和 `papers`；外部模式经 Go API 查询 Alexandria、HTSC-2025 对应表。`/share` 使用 Recharts 绘制 Tc-Pressure 与 Tc-Year 图表并支持图表组合叠加。01 上传并审核通过的论文是本地检索结果的事实来源之一。
