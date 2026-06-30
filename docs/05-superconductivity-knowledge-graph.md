# V. Superconductivity Development Knowledge Graph

## Definition

Superconductivity Development Knowledge Graph 指围绕超导体、论文、物性参数和结构化记录建立的可查询关系网络。当前代码中的知识图谱主要服务于 RAG 问答：它把超导体作为 subject，把 Tc、压力、lambda、omega_log 等物性作为 predicate/object 进行结构化查询。

## Current Status

当前状态是部分落地。`backend/rag/knowledge_graph.py` 已经提供知识图谱式查询，RAG 引擎会在回答某些问题时调用 KG 查询。但目前没有独立的知识图谱页面、可视化网络图、图数据库后端或用户可交互探索界面。

## What Exists Today

当前知识图谱能力主要体现在三个方面。

第一，结构化属性查询。代码可以查询已审核论文关联的超导记录，把超导体化学式、物性谓词和数值结果组织为 KG 结果。它支持按谓词、操作符和值进行过滤。

第二，属性汇总。`get_all_properties(subject)` 可以围绕某个超导体返回已知属性，用于回答某个材料的物性详情问题。

第三，RAG 融合。RAG 引擎会根据意图决定是否调用 KG 查询。如果用户问“哪些材料 Tc 高于 200K”或“某材料的 Tc 是多少”，系统更倾向使用结构化 KG 结果；如果用户问机理、综述或解释类问题，则更多依赖文本检索。

## Relationship With RAG

知识图谱不是 RAG 的同义词。RAG 是完整问答系统，包含意图解析、KG 查询、向量检索、重排序、prompt 构造和 LLM 生成。知识图谱是其中更结构化、更适合事实和数值问题的一层。

当前把知识图谱单列为第五大功能，是因为它表达了项目未来可以从“文献问答”走向“超导发展脉络和材料关系网络”的方向。但从代码现状看，它还不是独立产品化模块。

## Code and API Evidence

核心代码：

- `backend/rag/knowledge_graph.py`
- `backend/rag/rag/engine.py`
- `backend/rag/rag/prompts.py`
- `backend/rag/service.py`

间接入口：

- `POST /api/rag/chat`
- `POST /api/rag/chat/stream`
- `GET /api/rag/superconductors`
- `GET /api/rag/superconductors/{superconductor_id}`

当前没有 `/knowledge-graph` 页面，也没有 `/api/knowledge-graph/*` 独立路由。

## Data Sources

知识图谱主要从论文、超导体和超导记录中抽取结构化关系。关键字段包括：

- `Superconductor.chemical_formula`
- `Paper.review_status`
- `SuperconductorRecord.pressure_gpa`
- `SuperconductorRecord.mcmillan_tc`
- `SuperconductorRecord.allen_dynes_tc`
- `SuperconductorRecord.isotropic_eliashberg_tc`
- `SuperconductorRecord.anisotropic_eliashberg_tc`
- `SuperconductorRecord.experimental_tc`
- `SuperconductorRecord.lambda_value`
- `SuperconductorRecord.omega_log`

旧 RAG 迁移设计还提到 `paper_chunks` 表和 MySQL/SQLite 双配置边界，这影响 KG 和 RAG 的数据来源一致性。

## Boundary

当前 KG 只表达被代码显式查询的结构化关系，不应夸大为完整学科知识图谱。它没有覆盖所有材料关系、研究团队关系、引用网络、历史事件、争议观点、实验路线或社区互动。

## Future Direction

后续可以把 KG 产品化为独立页面，支持按元素、化学式、年份、压力、Tc、论文和结构关系浏览。也可以增加图谱可视化、时间线、引用网络、研究者节点，以及与外部数据库结果的关系融合。
