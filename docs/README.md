# SC-Wiki 文档入口

当前代码、配置和测试能够证明的功能事实，以 [`overview/README.md`](overview/README.md) 为唯一入口。该目录按大功能组织功能边界、当前行为、工作流程、约束、代码与测试、已知问题和相关变更记录。

## 功能目录

| 功能 | 当前入口 |
| --- | --- |
| 超导数据去中心化上传 | [`overview/01_Decentralized_Uploading_of_Superconductivity_Data/README.md`](overview/01_Decentralized_Uploading_of_Superconductivity_Data/README.md) |
| 去中心化维护与验证 | [`overview/02_Decentralized_Maintenance_and_Verification/README.md`](overview/02_Decentralized_Maintenance_and_Verification/README.md) |
| 超导数据搜索与数据库发现 | [`overview/03_Superconductivity_Data_Search_and_Database_Discovery/README.md`](overview/03_Superconductivity_Data_Search_and_Database_Discovery/README.md) |
| 超导发展知识图谱 | [`overview/04_Superconductivity_Development_Knowledge_Graph/README.md`](overview/04_Superconductivity_Development_Knowledge_Graph/README.md) |
| 检索增强 AI 问答 | [`overview/05_Retrieval-Augmented_AI_Question_Answering/README.md`](overview/05_Retrieval-Augmented_AI_Question_Answering/README.md) |
| AI 辅助 Tc 估算 | [`overview/06_AI_Assisted_Tc_Estimation/README.md`](overview/06_AI_Assisted_Tc_Estimation/README.md) |
| 研究者社区论坛 | [`overview/07_Researcher_Community_Forum/README.md`](overview/07_Researcher_Community_Forum/README.md) |

## 规格与部署

- 功能规格和评估材料位于 [`specs/`](specs/)。规格不代表已落地能力，当前状态以 `overview/` 为准。
- Docker 编排入口是 [`../docker/compose.yaml`](../docker/compose.yaml)。交付部署包的导入、启动和更新步骤位于 [`../docker/deploy/README.md`](../docker/deploy/README.md)。
- [`overview/02_Decentralized_Maintenance_and_Verification/deployment-and-runtime.md`](overview/02_Decentralized_Maintenance_and_Verification/deployment-and-runtime.md) 记录当前部署拓扑、配置边界和运行时约束。

## 维护规则

- 只把当前代码、配置或实际测试支持的事实写入 `overview/`。
- 未来方案、未完成能力和无法核验的历史描述必须明确标注，不得写成当前功能。
- 旧的顶层功能说明和知识图谱总结已迁移到 `overview/`，不再作为功能入口维护。
