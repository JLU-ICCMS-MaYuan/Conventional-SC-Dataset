# SC-Wiki 功能综述

本文档按当前代码真实状态，把 SC-Wiki 对外可讲的能力整理为七个大功能。`docs/overview/` 是功能文档的唯一入口；本页保留总览和七篇顶层说明，`docs/specs/` 存放仍在设计或评估中的规格文档，其他专题总结仅作历史或补充材料，不能替代功能总览。

## 七大功能

| 编号 | 功能 | 当前状态 | 说明文档 |
| --- | --- | --- | --- |
| I | Decentralized Uploading of Superconductivity Data | 已部分落地 | [01-decentralized-uploading.md](01-decentralized-uploading.md) |
| II | Decentralized Maintenance and Verification | 已部分落地 | [02-maintenance-and-verification.md](02-maintenance-and-verification.md) |
| III | Superconductivity Data Search and Database Discovery | 已落地 | [03-data-search-and-database-discovery.md](03-data-search-and-database-discovery.md) |
| IV | Superconductivity Development Knowledge Graph | 已落地 | [04-superconductivity-knowledge-graph.md](04-superconductivity-knowledge-graph.md) |
| V | Retrieval-Augmented AI Question Answering | 已落地 | [05-rag-question-answering.md](05-rag-question-answering.md) |
| VI | AI-Assisted Estimation of Superconducting Transition Temperatures | 已落地但实验性 | [06-ai-assisted-tc-estimation.md](06-ai-assisted-tc-estimation.md) |
| VII | Researcher Community Forum | 社区基础部分落地，论坛未落地 | [07-researcher-community-forum.md](07-researcher-community-forum.md) |

## 系统定位

SC-Wiki 是一个围绕元素体系、超导体化学式、论文来源和结构化物理记录组织的超导数据平台。它的主线不是通用全文文献库，也不是已经完成的社交论坛，而是让研究者提交结构化超导数据，经过维护与审核形成可信数据资产，再围绕元素组合查询本地数据、发现外部数据库候选材料，并进一步被知识图谱、RAG、预测工具和社区展示使用。

当前主业务数据模型包括：

- `periodic_table_elements`
- `chemical_systems`
- `superconductors`
- `papers`
- `users`
- `superconductor_records`
- `superconductors_structures`

RAG 子系统还使用 `paper_chunks`、Chroma 向量库和独立配置的数据根目录。主 MySQL 业务库、RAG 数据库和 Chroma 向量库在代码中存在边界，虽然它们服务于同一个站点。

## 当前主要入口

| 页面或接口 | 作用 |
| --- | --- |
| `/` | 首页（重定向到 /news） |
| `/news` | 首页快讯、诺贝尔奖里程碑、贡献统计展示 |
| `/search` | 周期表探索、数据检索与论文详情（Layer 3） |
| `/share` | 社区图表页：Tc-Pressure / Tc-Year 散点图，点击数据点查看论文详情 |
| `/upload` | 论文与超导记录上传 |
| `/rag` | AI 文献助手（普通问答 + 探索模式） |
| `/knowledge` | 知识图谱可视化 |
| `/tc-predict` | Tc 预测实验页 |
| `/admin` | 管理员后台（文献管理、用户管理、快讯管理） |
| `/api/knowledge-graph/*` | 知识图谱用户 API |
| `/api/kg/*` | 知识图谱 RAG API |
| `/api/alexandria/*` | Alexandria 外部数据库接口 |
| `/api/htsc2025/*` | HTSC-2025 外部数据集接口 |

## 功能边界

已经落地的能力包括周期表与化学式检索、论文详情（Layer 3 基础信息/关键物性/结构预览）、Alexandria/HTSC-2025 外部数据发现、论文与超导记录上传、CIF/POSCAR 结构上传与审核、管理员维护、RAG 问答（Mentor + Inspiration Agent）、知识图谱可视化与 API、Tc 预测实验、社区图表页（Tc-Year/Tc-Pressure 散点图 + 点击数据点查看论文详情 + 自定义图表组合）、贡献者排行。

部分落地的能力包括去中心化维护、研究者社区和批量导入。它们有数据库字段、后台能力、统计接口或内部查询基础，但还没有形成完整的面向终端用户的闭环。

未落地的能力包括真正的论坛帖子、评论区、弹幕、点赞、浏览量、热度排序、审核者排行的完整前端展示、预测结果持久化和预测结果审核入库。

## 文档维护原则

这些文档只描述当前代码和从当前代码自然推出的功能边界。规划能力必须明确写成未落地或未来方向，不能写成现状。跨功能的基础设施应并入它服务的功能，而不是单独膨胀成产品能力。
