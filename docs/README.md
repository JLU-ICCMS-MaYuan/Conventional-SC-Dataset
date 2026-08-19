# SC-Wiki 文档入口

当前代码、配置和测试能够证明的功能事实，以 [`overview/README.md`](overview/README.md) 为唯一入口。该目录按大功能组织功能边界、当前行为、工作流程、约束、代码与测试、已知问题和相关变更记录。

## 功能目录

| 功能 | 当前入口 |
| --- | --- |
| 材料与文献检索 | [`overview/01-material-search-and-discovery/README.md`](overview/01-material-search-and-discovery/README.md) |
| 数据模型与维护 | [`overview/02-data-model-and-maintenance/README.md`](overview/02-data-model-and-maintenance/README.md) |
| 晶体结构管理 | [`overview/03-crystal-structure-management/README.md`](overview/03-crystal-structure-management/README.md) |
| 认证与审核 | [`overview/04-authentication-and-review/README.md`](overview/04-authentication-and-review/README.md) |
| 可视化与统计 | [`overview/05-visualization-and-metrics/README.md`](overview/05-visualization-and-metrics/README.md) |
| RAG 文献助手 | [`overview/06-rag-literature-assistant/README.md`](overview/06-rag-literature-assistant/README.md) |
| 实验性 Tc 估算 | [`overview/07-experimental-tc-estimation/README.md`](overview/07-experimental-tc-estimation/README.md) |

## 规格与部署

- 功能规格和评估材料位于 [`specs/`](specs/)。规格不代表已落地能力，当前状态以 `overview/` 为准。
- Docker 编排入口是 [`../docker/compose.yaml`](../docker/compose.yaml)。交付部署包的导入、启动和更新步骤位于 [`../docker/deploy/README.md`](../docker/deploy/README.md)。
- [`overview/02-data-model-and-maintenance/deployment-and-runtime.md`](overview/02-data-model-and-maintenance/deployment-and-runtime.md) 记录当前部署拓扑、配置边界和运行时约束。

## 维护规则

- 只把当前代码、配置或实际测试支持的事实写入 `overview/`。
- 未来方案、未完成能力和无法核验的历史描述必须明确标注，不得写成当前功能。
- 旧的顶层功能说明和知识图谱总结已迁移到 `overview/`，不再作为功能入口维护。
