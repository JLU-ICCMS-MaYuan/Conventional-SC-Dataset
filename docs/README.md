# SC-Wiki 功能文档

本文档全部使用中文描述；保留 API、RAG、GNN、DOI、Tc、PDOS、CIF、POSCAR 等专业名词。

## 七个核心模块

| 编号 | 模块 | 状态 | 文档 |
| --- | --- | --- | --- |
| 01 | 去中心化超导数据上传 | 已部分落地 | [01-decentralized-uploading/README.md](01-decentralized-uploading/README.md) |
| 02 | 数据维护与审核 | 已部分落地 | [02-maintenance-and-verification/README.md](02-maintenance-and-verification/README.md) |
| 03 | 超导数据检索与数据库发现 | 已落地，结果页表格待重构 | [03-data-search-and-database-discovery/README.md](03-data-search-and-database-discovery/README.md) |
| 04 | 超导发展知识图谱 | 部分落地 | [04-superconductivity-knowledge-graph/README.md](04-superconductivity-knowledge-graph/README.md) |
| 05 | 检索增强问答 | 已落地 | [05-rag-question-answering/README.md](05-rag-question-answering/README.md) |
| 06 | AI 辅助 Tc 估算 | 已落地但实验性 | [06-ai-assisted-tc-estimation/README.md](06-ai-assisted-tc-estimation/README.md) |
| 07 | 研究者社区与图表论坛 | 社区基础部分落地，论坛未落地 | [07-researcher-community-forum/README.md](07-researcher-community-forum/README.md) |

## 文档维护规则

- 每个业务模块子目录固定包含 4 个 Markdown 文件：`README.md`、`frontend-design.md`、`backend-design.md`、`api-design.md`。
- `README.md` 写总体规划；其余三个文件分别写前端、后端和 API 设计。
- `docs/` 记录当前能力和自然演进边界；`future-plan/` 记录后续建设方案。
- 未落地能力必须明确标注为规划或「有待建设」。
