# V. Retrieval-Augmented AI Question Answering

## Definition

Retrieval-Augmented AI Question Answering 是 SC-Wiki 的 AI 文献助手能力。它把结构化数据库、知识图谱查询、向量检索和大语言模型回答结合起来，让用户用自然语言询问超导文献、材料和物性问题。

## Current Status

当前状态是已落地。代码中存在 `/rag` 页面、`/api/rag/*` 接口、内部 RAG service、知识图谱查询、SQL 搜索、Chroma 向量检索、PDF 摄入和 SSE 流式问答。实际可用性取决于 RAG 数据库、Chroma 路径和 LLM API 配置是否存在。

## User Experience

用户进入 `/rag` 后，可以进行文献搜索、自然语言问答和 PDF 上传摄入。前端支持流式输出、对话历史、本地缓存、引用编号和文献来源展示。旧文档中描述过 React 三栏布局：对话列表、流式聊天和文献来源栏。当前模板入口是 `frontend/templates/rag.html`，并引用构建后的静态资源；仓库中也保留了旧 `frontend/static/js/rag.js`。

回答过程不是纯 LLM 聊天。系统先判断问题意图，再按问题类型选择结构化 KG 查询、语义检索或二者融合，最后把检索证据交给 LLM 生成回答。

## Backend Flow

RAG 后端主要经过以下步骤：

1. 接收用户问题和多轮历史。
2. 检测搜索模式或提取问题意图。
3. 对结构化属性问题调用 knowledge graph 查询。
4. 对机制、综述或文本问题调用向量检索。
5. 对检索结果进行排序和上下文整理。
6. 构造融合 prompt。
7. 调用 LLM，非流式或 SSE 流式返回答案。
8. 返回引用论文、超导体或数据点信息。

RAG 的知识图谱和检索并非完全独立产品，而是 AI 问答链路中的检索层。独立的知识图谱功能在第四篇文档中单独说明；RAG 在它之上继续叠加向量索引、意图解析、上下文融合和 LLM 生成。

## Code and API Evidence

页面入口：

- `/rag`

后端入口：

- `backend/api/rag.py`
- `backend/rag/service.py`
- `backend/rag/rag/engine.py`
- `backend/rag/knowledge_graph.py`
- `backend/rag/search/*`
- `backend/rag/ingest/*`

接口包括：

- `GET /api/rag/health`
- `GET /api/rag/stats`
- `GET /api/rag/search/detect`
- `GET /api/rag/search`
- `POST /api/rag/chat`
- `POST /api/rag/chat/stream`
- `GET /api/rag/papers`
- `GET /api/rag/papers/{paper_id}`
- `GET /api/rag/superconductors`
- `GET /api/rag/superconductors/{superconductor_id}`
- `POST /api/rag/upload-pdf`

## Data Boundary

RAG 数据存储与主业务数据库存在边界。历史文档显示 RAG 原本读取 `RAG_DATA_ROOT/dev.db` 和 ChromaDB；后续设计又支持通过 `RAG_DATABASE_URL` 迁移到 MySQL。当前代码中 `backend/rag/config.py`、`backend/rag/database.py` 和 `backend/rag/service.py` 共同决定实际连接方式。

RAG 模型中有 `paper_chunks`，用于文献文本块。主业务模型中主要表是论文、超导体和超导记录。两者重叠但不完全一致。

## Limitations

RAG 问答质量依赖三个外部条件：是否有可用的结构化数据，是否有可用的 Chroma 向量库，是否配置 LLM API。系统可以在检索可用但聊天不可用时返回健康状态提示。

PDF 上传摄入属于 RAG 子系统，不等同于主业务的论文上传审核流程。PDF 摄入产生的内容是否进入主业务库、是否审核、是否公开，需要额外设计。

## Future Direction

后续可以把 RAG 的 PDF 摄入与主上传审核流程打通，让 AI 提取出的结构化数据进入待审核队列；也可以让回答引用更稳定地映射到主业务记录、结构和外部数据库来源。
