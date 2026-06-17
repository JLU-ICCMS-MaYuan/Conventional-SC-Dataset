# RAG HTTP 集成设计

日期：2026-06-17

## 摘要

SC-Wiki 将通过 HTTP 方式接入相邻项目 `../Conventional-SC-Dataset-talk` 的 RAG 能力。SC-Wiki 新增独立 `/rag` 页面，并在后端新增 `/api/rag/*` 薄代理接口。talk 项目保持独立 FastAPI 服务，继续负责 RAG 搜索、问答、SQLite/Chroma 访问和 LLM 调用。

第一版公开访问、非流式输出，并支持服务不可用时友好降级。第一版同时支持搜索和问答，但不持久化聊天历史，也不合并两个代码库。

## 目标

- 在 SC-Wiki 首页增加“AI 文献助手”入口。
- 在 SC-Wiki 中新增独立 `/rag` 页面。
- SC-Wiki 前端只调用 SC-Wiki 自身 API，不直接访问 talk 服务。
- 由 SC-Wiki 后端代理搜索和非流式问答请求到 talk 服务。
- talk 服务不可用时，SC-Wiki 页面和接口能够友好降级。

## 非目标

- 第一版不支持流式/SSE 输出。
- 不支持多轮聊天记忆。
- 不做登录限制、额度、审计日志或使用统计。
- 不把 RAG 问题或答案写入 SC-Wiki 数据库。
- 不让 SC-Wiki 直接连接 talk 服务的 SQLite 数据库或 Chroma 目录。
- 不把 `hydride_rag` 代码级合并到 SC-Wiki。

## 架构

集成边界分为三层：

1. **SC-Wiki 前端**
   - 在首页增加入口按钮，跳转到 `/rag`。
   - 新增 `/rag` 页面，保持现有 Bootstrap 和静态 JS 风格。
   - 调用 `/api/rag/health`、`/api/rag/search`、`/api/rag/chat`。

2. **SC-Wiki 后端代理**
   - 新增 `backend/api/rag.py`，并在 `backend/main.py` 注册路由。
   - 使用 `httpx` 调用 talk 服务。
   - 统一处理配置、输入校验、超时、连接失败和非 2xx 响应。

3. **Conventional-SC-Dataset-talk 服务**
   - 独立运行，例如：
     ```bash
     uvicorn hydride_rag.api.app:app --host 0.0.0.0 --port 8001
     ```
   - 负责 RAG 搜索、RAG 问答、SQLite/Chroma 访问和 LLM 行为。

SC-Wiki 是产品入口和代理层；talk 服务是 RAG 能力提供方。

## 配置

SC-Wiki 新增环境变量：

```bash
RAG_SERVICE_URL=http://127.0.0.1:8001
RAG_SERVICE_TIMEOUT=30
```

默认值：

- `RAG_SERVICE_URL`：`http://127.0.0.1:8001`
- `RAG_SERVICE_TIMEOUT`：`30` 秒

服务地址只在 SC-Wiki 服务端使用，浏览器不需要知道 talk 服务地址。

## SC-Wiki 后端 API

### `GET /api/rag/health`

检查 talk 服务是否可访问。

成功响应：

```json
{
  "available": true,
  "service_url_configured": true
}
```

不可用响应：

```json
{
  "available": false,
  "service_url_configured": true,
  "message": "AI 文献助手服务暂不可用"
}
```

该接口不应因为 talk 服务关闭而返回 500。

### `GET /api/rag/search?q=LaH10&top_k=10`

代理搜索请求到 talk 服务。

校验规则：

- `q` 去除首尾空白后不能为空。
- `top_k` 限制在较小范围内，例如 1-20。

响应形态：

```json
{
  "ok": true,
  "data": {
    "mode": "formula",
    "query": "LaH10",
    "superconductors": [],
    "papers": [],
    "chunks": [],
    "related_paper_ids": [],
    "total": 0
  }
}
```

代理层应将 talk 服务返回内容保留在 `data` 字段中，不重新建模所有 RAG 字段。

### `POST /api/rag/chat`

代理非流式问答请求到 talk 服务。

请求：

```json
{
  "question": "LaH10 的 Tc 和压力范围是什么？"
}
```

校验规则：

- `question` 去除首尾空白后不能为空。

响应形态：

```json
{
  "ok": true,
  "data": {
    "answer": "LaH10 在示例文献中通常对应高压氢化物超导体，具体 Tc 和压力应以返回引用为准。",
    "chunks_used": 5,
    "citations": [],
    "model": "deepseek-chat",
    "source": "rag",
    "papers": {},
    "top10": []
  }
}
```

当前 talk 服务通过 `POST /api/chat` 提供该能力，返回 `answer`、`chunks_used`、`citations`、`model`、`source`、可选 `papers` 和可选 `top10`。SC-Wiki 前端应把 `citations` 作为来源信息展示。SC-Wiki 不生成或改写答案，答案生成仍由 talk 服务负责。

## 数据流

```text
用户打开 /rag
  -> 前端调用 /api/rag/health
  -> SC-Wiki 后端调用 talk 健康检查或 API 入口
  -> 前端展示已连接或不可用状态

用户搜索或提问
  -> 前端调用 /api/rag/search 或 /api/rag/chat
  -> SC-Wiki 后端校验输入
  -> SC-Wiki 后端使用 httpx 调用 talk 服务
  -> talk 服务查询 SQLite/Chroma/LLM
  -> SC-Wiki 包装结果
  -> 前端渲染答案、结果分组或友好错误提示
```

## UI 设计

### 首页

在首页现有操作按钮附近增加一个始终可见的入口：

```text
🤖 AI 文献助手
```

按钮跳转到 `/rag`。talk 服务不可用时也不隐藏该按钮；可用性说明放在 `/rag` 页面内展示。

### `/rag` 页面

页面沿用现有 Bootstrap 风格，并在合适时复用已有通用脚本，例如语言切换和登录态辅助脚本。

页面分区：

1. **服务状态**
   - 页面加载后调用 `/api/rag/health`。
   - 可用时显示轻量连接状态。
   - 不可用时显示 warning 提示：“AI 文献助手服务暂不可用，请稍后再试。”
   - 不可用时禁用搜索和提问按钮，但输入框仍可编辑。

2. **自然语言问答**
   - 一个用于输入问题的 textarea。
   - 一个提交按钮。
   - 等待响应期间显示非流式 loading 状态。
   - 渲染返回的答案。
   - 如果存在来源或引用信息，在答案下方展示。

3. **搜索**
   - 一个搜索输入框，支持化学式、元素体系、论文关键词或自然语言。
   - 第一版固定使用 `top_k=10`，避免不必要的 UI 复杂度。
   - 按返回字段分组渲染结果：
     - `superconductors`
     - `papers`
     - `chunks`
   - 缺失的结果分组显示为空状态，不视为错误。

搜索和问答相互独立。执行搜索不会自动触发问答。

## 错误处理

SC-Wiki 代理层统一处理以下情况：

1. **连接失败 / talk 服务未启动**
   - 健康检查返回 `available: false`。
   - 搜索/问答返回 503 和 JSON 错误。

2. **超时**
   - 使用 `RAG_SERVICE_TIMEOUT`。
   - 返回 504，消息为：“AI 文献助手响应超时，请稍后重试”。

3. **空输入**
   - 搜索 query 或问答 question 为空时返回 400。
   - 前端提交前也做一次校验。

4. **talk 服务返回非 2xx**
   - 不透传 HTML 错误页面。
   - 返回统一 JSON：
     ```json
     {
       "ok": false,
       "message": "AI 文献助手返回错误",
       "detail": "talk service returned HTTP 500 while handling /api/chat"
     }
     ```

5. **返回结构不符合预期**
   - 前端防御式渲染。
   - 缺失 `answer`、`sources`、`superconductors`、`papers` 或 `chunks` 不会导致页面崩溃。

## 测试策略

后端测试聚焦 SC-Wiki 代理契约，不测试 RAG 答案质量。

建议后端测试：

- `GET /api/rag/health`
  - talk 服务可用时返回 `available: true`。
  - talk 服务不可用时返回 `available: false`，而不是 500。
- `GET /api/rag/search`
  - 空查询返回 400。
  - 正常代理响应返回 `ok: true`。
  - 连接失败返回 503。
  - 超时返回 504。
- `POST /api/rag/chat`
  - 空问题返回 400。
  - 正常代理响应返回 `ok: true`。
  - 连接失败或超时返回预期状态码和消息。

手动/前端检查：

- 首页显示“AI 文献助手”，并能跳转到 `/rag`。
- talk 服务关闭时，`/rag` 仍能打开，并显示禁用状态和友好不可用提示。
- 本地启动 talk 服务后，搜索和问答能渲染返回数据。

## 实施注意事项

- 代理逻辑保持小而独立，集中在 `backend/api/rag.py`。
- 在 `backend/main.py` 中像现有 API 模块一样注册 router。
- 新增 `frontend/templates/rag.html` 页面和聚焦的 `frontend/static/js/rag.js` 脚本。
- 第一版不增加持久化表或迁移。
- 不从 SC-Wiki 导入 `hydride_rag`；只通过 HTTP 通信。
