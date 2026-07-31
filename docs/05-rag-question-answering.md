# V. Retrieval-Augmented AI Question Answering

## Definition

Retrieval-Augmented AI Question Answering 是 SC-Wiki 的 AI 文献助手能力。它集成了 Neo4j 知识图谱、Chroma 向量检索、MySQL 物性查询和大语言模型，支持两种模式：普通问答（Mentor Agent）和灵感探索（Inspiration Agent）。

## Current Status

当前状态已落地。`/rag` 页面提供完整的对话交互，支持流式输出、对话历史、多轮对话和探索模式。后端已从硬编码意图路由升级为 LangGraph Agent 架构。

## 两种模式

### 普通问答（Mentor Agent）

位于 `backend/rag/agent/mentor.py`。LangGraph 图：mentor → router → tools/ask_user/end。

LLM 可自主调用 7 个 Tool：
- `search_papers` — Neo4j 标题搜索
- `paper_context` — Neo4j 论文全貌
- `material_info` — Neo4j 材料全貌
- `explore_graph` — Neo4j 图遍历
- `paper_path` — Neo4j 最短路径
- `search_literature` — Chroma 语义搜索
- `query_properties` — MySQL 物性查询

### 灵感探索（Inspiration Agent）

位于 `backend/rag/agent/graph.py`。LangGraph 三阶段图：clarify → design → discuss。

- **Stage 1 澄清**：LLM 提问了解用户研究方向、方法、约束（≥2 条信息满足 → 进入 Stage 2）
- **Stage 2 设计**：router(选思考模式) → search(Chroma 检索) → curator(LLM 筛选) → evidence(生成 IdeaCard) → reviewer(审稿评分)
- **Stage 3 讨论**：总结方案 + 审稿意见，邀请用户反馈；可回到 Stage 2 重新设计

5 种思考模式保留：gap_detector / analogy_engine / contradiction_catalyst / composition_walker / counterfactual_reasoner。

## Backend Architecture

```
backend/rag/
├── agent/
│   ├── graph.py         # Inspiration Agent 三阶段图
│   ├── mentor.py        # Mentor Agent 导师图
│   ├── state.py         # AgentState / InspirationState
│   └── tools.py         # 7 个 LangChain Tool
├── tools/
│   ├── neo4j.py         # Neo4j 图查询
│   ├── mysql.py         # MySQL 物性查询
│   └── chroma.py        # Chroma 语义搜索
├── core/
│   ├── engine.py        # 旧问答引擎（保留）
│   └── prompts.py
├── inspiration/         # 探索模式五步流水线
├── search/              # 向量搜索 + SQL 搜索 + 融合
├── models/              # RAG 数据模型
├── config.py            # 配置
├── database.py          # RAG DB
├── vectordb.py          # Chroma 封装
└── service.py           # 服务门面
```

## API

页面入口：
- `/rag`

接口：
- `GET /api/rag/health`
- `GET /api/rag/stats`
- `GET /api/rag/search`
- `POST /api/rag/chat`
- `POST /api/rag/chat/stream` — `explore=true` 走 Inspiration Agent，`explore=false` 走 Mentor Agent
- `GET /api/rag/papers`
- `GET /api/rag/papers/{paper_id}`
- `GET /api/rag/superconductors`
- `GET /api/rag/superconductors/{superconductor_id}`
- `POST /api/rag/upload-pdf`

## Data Sources

RAG 使用三个数据源：
- **Neo4j**：论文关系图、材料上下文、图遍历、最短路径
- **Chroma**：20 个向量集合（paper_chunks 29311 条 + paper_summaries 638 条 + 18 个专题集合）
- **MySQL**：物性查询（Tc/压力/lambda/omega_log）

## Limitations

- Inspiration Agent 尚未实现真正的流式 token 输出（当前是整个 answer 生成后一次性发送）
- Old engine.py 的简单问答路径保留在 `core/engine.py`，但 `explore=False` 的流量已走 mentor.py

## Future Direction

- Inspiration Agent 流式 token 输出
- Agent 多轮状态持久化（LangGraph Checkpointer）
- 探索模式中接入 Neo4j 图遍历 Tool
