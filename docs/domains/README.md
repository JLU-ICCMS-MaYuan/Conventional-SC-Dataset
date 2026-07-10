# 领域文档

本目录描述 SC-Wiki 已由代码、测试或配置证实的当前行为。单次交付计划在
`specs/`，运行约束在 `docs/operations/`，术语与长期背景从
`docs/memory/README.md` 进入。

| 领域 | 当前事实 |
| --- | --- |
| [core-superconductor-catalog.md](core-superconductor-catalog.md) | 元素、化学体系、超导体、文献与记录的主数据模型。 |
| [search-and-external-catalogs.md](search-and-external-catalogs.md) | 主库、Alexandria 与 HTSC-2025 的发现入口。 |
| [contribution-upload-and-review.md](contribution-upload-and-review.md) | 用户、管理员、文献审核与图表可见性。 |
| [crystal-structure-lifecycle.md](crystal-structure-lifecycle.md) | 晶体结构上传、审核和默认结构选择。 |
| [rag-and-knowledge-graph.md](rag-and-knowledge-graph.md) | 独立 RAG 数据面、检索、问答与关系查询。 |
| [tc-prediction.md](tc-prediction.md) | 基于 CONTCAR/PDOS 的即时 Tc 估算。 |
| [researcher-contribution-metrics.md](researcher-contribution-metrics.md) | 贡献排行和公开图表指标。 |

每页的“已知缺口”必须对应或最终创建 GitHub `type:doc-debt`、`type:idea`
或 `type:bug` Issue；在 Issue 创建前不得把缺口误写为当前能力。
