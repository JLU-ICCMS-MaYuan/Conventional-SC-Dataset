# 材料与文献检索

## 功能边界

该功能负责从元素组合、化学式和超导体记录出发查询本地论文与物性数据，并补充 Alexandria、HTSC-2025 等外部候选材料。当前前端入口是 `/search`，在同一页面内完成周期表选择、结果筛选、来源切换、论文详情和结构预览。

该功能不负责修改权威数据、审核论文、摄入 RAG 文档或保证外部数据表始终存在。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [本地材料检索](local-material-search.md) | 按化学式或元素关系检索临界温度物性记录 | Go API、MySQL、`key_properties` |
| [外部数据集检索](external-dataset-search.md) | 查询 Alexandria 和 HTSC-2025 候选材料 | Go API、外部数据表 |
| [论文与物性结果](paper-and-property-results.md) | 组织论文、关键物性、结构预览和多源搜索结果 | 本地材料检索、论文关系 |
| [超导知识图谱](superconductivity-knowledge-graph.md) | 展示 `graph.json` 快照和 Neo4j 工具查询 | Go API、Python KG API、Neo4j |
| [分享与导出](share-and-export.md) | 输出 JSON、RIS 等分享数据 | 论文与物性结果 |

## 功能组成

```text
材料与文献检索
├── 本地材料检索
├── 外部数据集检索
├── 论文与物性结果
├── 超导知识图谱
└── 分享与导出
```

## 关联关系

用户从 `/search` 的周期表或化学式输入进入检索。本地模式经 Go API 查询 `chemical_systems`、`superconductors`、`key_properties` 和 `papers`；外部模式经 Go API 查询 Alexandria、HTSC-2025 对应表。页面会把来源差异映射为统一结果行，并允许查看论文详情或结构预览。
