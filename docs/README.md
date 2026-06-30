# SC-Wiki 功能综述

本文档按当前代码真实状态，把 SC-Wiki 对外可讲的能力整理为七个大功能。旧文档中的晶体结构能力已并入数据上传，首页图表与贡献排行已并入研究者社区，导入导出、迁移和备份已并入维护与验证。因此当前文档只保留一篇综述和七篇功能说明。

## 七大功能

| 编号 | 功能 | 当前状态 | 说明文档 |
| --- | --- | --- | --- |
| I | Decentralized Uploading of Superconductivity Data | 已部分落地 | [01-decentralized-uploading.md](01-decentralized-uploading.md) |
| II | Decentralized Maintenance and Verification | 已部分落地 | [02-maintenance-and-verification.md](02-maintenance-and-verification.md) |
| III | Retrieval-Augmented AI Question Answering | 已落地 | [03-rag-question-answering.md](03-rag-question-answering.md) |
| IV | AI-Assisted Estimation of Superconducting Transition Temperatures | 已落地但实验性 | [04-ai-assisted-tc-estimation.md](04-ai-assisted-tc-estimation.md) |
| V | Superconductivity Development Knowledge Graph | 部分落地 | [05-superconductivity-knowledge-graph.md](05-superconductivity-knowledge-graph.md) |
| VI | Researcher Community Forum | 社区基础部分落地，论坛未落地 | [06-researcher-community-forum.md](06-researcher-community-forum.md) |
| VII | External Superconductivity Database Discovery | 已落地 | [07-external-database-discovery.md](07-external-database-discovery.md) |

## 系统定位

SC-Wiki 是一个围绕元素体系、超导体化学式、论文来源和结构化物理记录组织的超导数据平台。它的主线不是通用全文文献库，也不是已经完成的社交论坛，而是让研究者围绕元素组合快速发现超导体系，提交结构化数据，经过维护与审核后进入可查询、可展示、可被 AI 检索使用的数据资产。

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
| `/` | 首页、周期表入口、图表与统计展示 |
| `/elements` | 周期表内容页 |
| `/compound/{element_symbols}` | 元素体系和化学式检索结果页 |
| `/login`、`/register` | 用户登录与注册 |
| `/admin/register` | 管理员申请注册 |
| `/admin/dashboard` | 管理员审核面板 |
| `/admin/superadmin` | 超级管理员审批和权限管理 |
| `/admin/papers` | 全局文献管理 |
| `/admin/users` | 用户管理 |
| `/rag` | AI 文献助手 |
| `/tc-pre` | Tc 预测实验页 |
| `/api/alexandria/*` | Alexandria 外部数据库接口 |
| `/api/htsc2025/*` | HTSC-2025 外部数据集接口 |

## 功能边界

已经落地的能力包括周期表与化学式检索、论文与超导记录上传、CIF/POSCAR 结构上传与审核、管理员维护、RAG 问答、Tc 预测实验、首页 Tc-Year/Tc-Pressure 图表、贡献者排行，以及 Alexandria/HTSC-2025 外部数据发现。

部分落地的能力包括去中心化维护、研究者社区、知识图谱产品化和批量导入。它们有数据库字段、后台能力、统计接口或内部查询基础，但还没有形成完整的面向终端用户的闭环。

未落地的能力包括真正的论坛帖子、评论区、弹幕、点赞、浏览量、热度排序、审核者排行的完整前端展示、图表点击联动检索、预测结果持久化和预测结果审核入库。

## 文档维护原则

这些文档只描述当前代码和从当前代码自然推出的功能边界。规划能力必须明确写成未落地或未来方向，不能写成现状。跨功能的基础设施应并入它服务的功能，而不是单独膨胀成产品能力。
