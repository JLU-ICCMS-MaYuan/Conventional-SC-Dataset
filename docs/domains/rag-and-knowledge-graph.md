# RAG 与关系查询

## 职责

RAG 是独立于主库的数据面，提供结构化搜索、向量检索、引用支撑问答和 SSE 流式
回答。知识图谱不是独立产品页面，而是对已审核 RAG 文献记录的受限关系查询投影。

## 当前接口

- `/api/rag/health`、`/stats`、`/search`、`/chat`、`/chat/stream` 提供可用性、检索
  和问答入口。
- `/api/rag/upload-pdf` 临时保存 PDF，交给摄入服务抽取和写入；接口只接受 PDF。
- 问答编排可结合意图识别、关系查询、向量检索和 LLM；流式端点使用
  `text/event-stream`。

## 数据与边界

- RAG 使用独立关系数据库和 Chroma 持久化向量集合，配置由 `RagSettings` 管理。
- 关系查询只读取已审核记录；它不意味着存在独立的知识图谱路由、页面或图数据库。

## 证据

- `backend/api/rag.py`
- `backend/rag/service.py`
- `backend/rag/rag/engine.py`
- `backend/rag/knowledge_graph.py`
- `backend/rag/config.py`
- `tests/04_superconductivity_knowledge_graph/test_knowledge_graph.py`

## 已知缺口

- 探索模式中部分关系查询调用仍处于待恢复状态；不要承诺为稳定探索功能。
- RAG 上传的认证、主库审核 UI 衔接和主/RAG 数据同步尚缺权威设计，应建立相应
  GitHub Issue。
