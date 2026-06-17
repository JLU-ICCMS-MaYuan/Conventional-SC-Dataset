# RAG 代码级同进程集成设计

日期：2026-06-17

## 摘要

本设计将当前 SC-Wiki 中的 RAG HTTP 代理集成升级为代码级同进程集成。SC-Wiki 不再要求额外启动 `../Conventional-SC-Dataset-talk` 的 FastAPI 服务，而是在自身进程内直接调用迁入的 RAG 搜索和问答模块。

第一版只迁移运行搜索和非流式问答所需的最小闭环代码。RAG 数据仍复用相邻项目 `../Conventional-SC-Dataset-talk` 中已有的 `dev.db` 和 `chroma_db`，不复制大体积数据库或向量库。

## 目标

- 将 RAG 搜索和问答代码迁入 SC-Wiki 当前分支。
- 保持 `/rag` 页面和 `/api/rag/*` 前端契约不变。
- SC-Wiki 单进程启动后即可提供 RAG 搜索能力。
- 配置 `DEEPSEEK_API_KEY` 后，SC-Wiki 单进程即可提供真实非流式问答能力。
- 不再因为 talk uvicorn 服务未启动而显示“AI 文献助手服务暂不可用”。

## 非目标

- 不复制 `../Conventional-SC-Dataset-talk/dev.db`。
- 不复制 `../Conventional-SC-Dataset-talk/chroma_db`。
- 不迁移 talk 项目的独立 FastAPI app。
- 不迁移 PDF 上传、摄入、抽取、入库管线。
- 不迁移 `scripts/`、`PythonScripts/` 或遗留维护脚本。
- 不实现流式/SSE 输出。
- 不实现多轮聊天记忆、额度、审计或问答持久化。

## 架构边界

### SC-Wiki 前端

继续使用现有页面和脚本：

- `frontend/templates/rag.html`
- `frontend/static/js/rag.js`

前端接口保持不变：

- `GET /api/rag/health`
- `GET /api/rag/search?q=...&top_k=...`
- `POST /api/rag/chat`

### SC-Wiki RAG API 层

保留 `backend/api/rag.py` 作为 API 门面，但内部实现从 HTTP 代理改为函数调用：

```python
from backend.rag.service import health, search, chat
```

API 层职责：

- 校验输入。
- 调用内部 RAG service。
- 把内部异常映射为稳定 HTTP 响应。
- 保持返回给前端的 JSON 形态兼容当前页面。

### 内部 RAG 子系统

新增目录：

```text
backend/rag/
```

职责：

- 连接相邻 talk 项目的 RAG SQLite 数据库。
- 连接相邻 talk 项目的 Chroma 向量库。
- 提供 SQL 搜索、向量搜索、融合检索、知识图谱路由和非流式问答。
- 隔离 RAG 依赖，避免散落到 SC-Wiki 其他模块。

### 相邻 talk 项目

`../Conventional-SC-Dataset-talk` 第一版仍作为数据来源和代码参考保留，但不需要运行其 uvicorn 服务。

## 迁移范围

### 迁入模块

从 `../Conventional-SC-Dataset-talk/src/hydride_rag` 迁入以下运行时模块，并调整 import 到 `backend.rag`：

```text
backend/rag/
├── __init__.py
├── config.py
├── database.py
├── vectordb.py
├── knowledge_graph.py
├── service.py
├── models/
├── search/
└── rag/
```

其中：

- `config.py`：读取 RAG 数据路径和 DeepSeek 配置。
- `database.py`：创建连接 RAG `dev.db` 的 async SQLAlchemy engine/session。
- `vectordb.py`：连接 RAG `chroma_db`。
- `knowledge_graph.py`：保留结构化问答路由所需逻辑。
- `models/`：保留 RAG SQLite ORM 模型。
- `search/`：保留 SQL 搜索、向量搜索和融合逻辑。
- `rag/`：保留 prompt、reranker、`ask()` 等问答逻辑。
- `service.py`：新增 SC-Wiki 内部稳定门面，供 `backend/api/rag.py` 调用。

### 不迁入模块

以下模块第一版不迁入：

```text
hydride_rag/api/
hydride_rag/ingest/
scripts/
PythonScripts/
chroma_db/
dev.db
```

## 配置设计

### 数据路径配置

新增 RAG 专用环境变量：

```bash
RAG_DATA_ROOT=/home/work/workshop/git/Conventional-SC-Dataset-talk
RAG_DATABASE_URL=sqlite+aiosqlite:////home/work/workshop/git/Conventional-SC-Dataset-talk/dev.db
RAG_CHROMA_PATH=/home/work/workshop/git/Conventional-SC-Dataset-talk/chroma_db
```

默认值按当前仓库相对路径推导：

```text
SC-Wiki/../Conventional-SC-Dataset-talk/
```

默认文件：

```text
../Conventional-SC-Dataset-talk/dev.db
../Conventional-SC-Dataset-talk/chroma_db
```

### LLM 配置

沿用 talk 项目现有命名：

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

如果未配置 `DEEPSEEK_API_KEY`：

- 搜索仍可用。
- `/api/rag/health` 返回 `available: true`，但 `chat_available: false`。
- `/api/rag/chat` 返回 503，提示 `LLM 问答未配置`。

## API 行为

### `GET /api/rag/health`

同进程版本检查内部依赖状态：

- RAG SQLite 文件是否存在。
- SQLite 是否可连接并执行轻量查询。
- Chroma 目录是否存在。
- LLM 问答配置是否存在。

完全可用时返回：

```json
{
  "available": true,
  "database_available": true,
  "chroma_available": true,
  "chat_available": true,
  "message": "AI 文献助手已就绪"
}
```

检索可用但 LLM 未配置时返回：

```json
{
  "available": true,
  "database_available": true,
  "chroma_available": true,
  "chat_available": false,
  "message": "RAG 检索可用，LLM 问答未配置"
}
```

数据不可用时返回：

```json
{
  "available": false,
  "database_available": false,
  "chroma_available": false,
  "chat_available": false,
  "message": "AI 文献助手数据不可用"
}
```

### `GET /api/rag/search`

请求：

```http
GET /api/rag/search?q=LaH10&top_k=10
```

内部调用：

```python
await backend.rag.service.search("LaH10", top_k=10)
```

返回保持：

```json
{
  "ok": true,
  "data": {
    "mode": "formula",
    "query": "LaH10",
    "superconductors": [],
    "chunks": [],
    "papers": [],
    "related_paper_ids": [],
    "total": 0
  }
}
```

错误：

- 空查询：400 `搜索内容不能为空`
- 数据不可用：503 `AI 文献助手数据不可用`
- 内部异常：502 `AI 文献助手返回错误`

### `POST /api/rag/chat`

请求：

```json
{
  "question": "LaH10 的 Tc 和压力范围是什么？"
}
```

内部调用：

```python
await backend.rag.service.chat("LaH10 的 Tc 和压力范围是什么？")
```

返回保持：

```json
{
  "ok": true,
  "data": {
    "answer": "...",
    "chunks_used": 5,
    "citations": [],
    "model": "deepseek-chat",
    "source": "rag",
    "papers": {},
    "top10": []
  }
}
```

错误：

- 空问题：400 `问题不能为空`
- LLM 未配置：503 `LLM 问答未配置`
- 数据不可用：503 `AI 文献助手数据不可用`
- 内部异常：502 `AI 文献助手返回错误`

## 前端调整

`frontend/static/js/rag.js` 第一版只需要增强健康状态处理：

- `available: false`：搜索和问答按钮都禁用。
- `available: true` 且 `chat_available: false`：搜索按钮启用，问答按钮禁用。
- `available: true` 且 `chat_available: true`：搜索和问答按钮都启用。

页面不再出现“talk 服务暂不可用”的语义，而改为内部数据/LLM 配置状态。

## 测试策略

### 后端 API 测试

新增或改造：

```text
tests/test_rag_internal_api.py
```

覆盖：

- 健康检查识别数据可用状态。
- 健康检查识别 LLM 未配置状态。
- 搜索空查询返回 400。
- monkeypatch `backend.rag.service.search()` 时 `/api/rag/search` 返回 `{"ok": true, "data": ...}`。
- monkeypatch `backend.rag.service.chat()` 时 `/api/rag/chat` 返回 `{"ok": true, "data": ...}`。
- 数据不可用异常映射为 503。
- LLM 未配置异常映射为 503。

### import 测试

新增：

```text
tests/test_rag_internal_imports.py
```

覆盖：

```python
from backend.rag.config import get_rag_settings
from backend.rag.search.engine import search
from backend.rag.rag.engine import ask
```

确保迁移后的运行时 import 不再依赖顶层 `hydride_rag` 包。

### 轻量真实集成测试

当相邻数据存在时运行：

```python
pytest.mark.skipif(not dev_db.exists() or not chroma_dir.exists(), reason="RAG data not available")
```

覆盖：

- `backend.rag.service.health()` 能识别数据路径。
- `backend.rag.service.search("LaH10", top_k=3)` 返回标准结构。

不要求结果数量大于 0，避免测试依赖具体数据内容。

### 手动验证

只启动 SC-Wiki：

```bash
PYTHONPATH=. \
DATABASE_URL="sqlite:////home/work/workshop/git/SC-Wiki/data/dev.db" \
DEEPSEEK_API_KEY=... \
conda run -n Conventional-SC-Dataset \
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

验证：

```bash
curl http://127.0.0.1:8010/api/rag/health
curl "http://127.0.0.1:8010/api/rag/search?q=LaH10&top_k=3"
curl -X POST http://127.0.0.1:8010/api/rag/chat \
  -H "Content-Type: application/json" \
  --data '{"question":"LaH10 的 Tc 和压力范围是什么？"}'
```

浏览器验证：

- 打开 `/rag`。
- 不启动 talk uvicorn。
- 搜索可用。
- 配置 LLM 后问答可用。
- 未配置 LLM 时，页面明确显示“RAG 检索可用，LLM 问答未配置”。

## 风险与约束

- 同进程集成会把 RAG 依赖带入 SC-Wiki 运行环境，依赖缺失会影响 `/api/rag/*`。
- RAG 的 async SQLAlchemy 与 SC-Wiki 当前同步 SQLAlchemy 并存，必须隔离 engine/session，不能复用 `backend.database`。
- Chroma 和 LLM 初始化应延迟到调用时，避免影响 SC-Wiki 首页启动。
- 第一版不复制数据，因此部署时必须确保 `RAG_DATA_ROOT` 指向有效 talk 数据目录。
