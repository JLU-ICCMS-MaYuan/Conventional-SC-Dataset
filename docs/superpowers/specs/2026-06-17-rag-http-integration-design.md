# RAG HTTP Integration Design

Date: 2026-06-17

## Summary

SC-Wiki will integrate `../Conventional-SC-Dataset-talk` as an external RAG capability through HTTP. SC-Wiki will add an independent `/rag` page and a thin backend proxy under `/api/rag/*`. The talk project remains a separately running FastAPI service that owns RAG search, question answering, SQLite/Chroma access, and LLM calls.

The first version is public, non-streaming, and failure-tolerant. It supports both search and Q&A, but does not persist chat history or merge the two codebases.

## Goals

- Add an “AI 文献助手” entry point on the SC-Wiki home page.
- Add a standalone `/rag` page in SC-Wiki.
- Let the SC-Wiki frontend call only SC-Wiki APIs, not the talk service directly.
- Proxy search and non-streaming chat requests from SC-Wiki to the talk service.
- Degrade gracefully when the talk service is unavailable.

## Non-goals

- No streaming/SSE output in the first version.
- No multi-turn chat memory.
- No login requirement, quota, audit log, or usage tracking.
- No SC-Wiki database persistence for RAG questions or answers.
- No direct SC-Wiki connection to the talk service SQLite database or Chroma directory.
- No code-level merge of `hydride_rag` into SC-Wiki.

## Architecture

The integration has three boundaries:

1. **SC-Wiki frontend**
   - Adds a home-page button linking to `/rag`.
   - Adds a new `/rag` page using the existing Bootstrap/static-JS style.
   - Calls `/api/rag/health`, `/api/rag/search`, and `/api/rag/chat`.

2. **SC-Wiki backend proxy**
   - Adds `backend/api/rag.py` and registers it in `backend/main.py`.
   - Uses `httpx` to call the talk service.
   - Normalizes configuration, validation, timeouts, connection failures, and non-2xx responses.

3. **Conventional-SC-Dataset-talk service**
   - Runs independently, for example:
     ```bash
     uvicorn hydride_rag.api.app:app --host 0.0.0.0 --port 8001
     ```
   - Owns RAG search, RAG chat, SQLite/Chroma access, and LLM behavior.

SC-Wiki is the product shell and proxy. The talk service is the RAG provider.

## Configuration

SC-Wiki adds these environment variables:

```bash
RAG_SERVICE_URL=http://127.0.0.1:8001
RAG_SERVICE_TIMEOUT=30
```

Defaults:

- `RAG_SERVICE_URL`: `http://127.0.0.1:8001`
- `RAG_SERVICE_TIMEOUT`: `30` seconds

The configured URL is only used server-side by SC-Wiki. The browser should not need to know the talk service address.

## SC-Wiki Backend API

### `GET /api/rag/health`

Checks whether the talk service is reachable.

Success response:

```json
{
  "available": true,
  "service_url_configured": true
}
```

Unavailable response:

```json
{
  "available": false,
  "service_url_configured": true,
  "message": "AI 文献助手服务暂不可用"
}
```

This endpoint should not return 500 just because the talk service is down.

### `GET /api/rag/search?q=LaH10&top_k=10`

Proxies search to the talk service.

Validation:

- `q` must be non-empty after trimming.
- `top_k` should be constrained to a small range, such as 1-20.

Response shape:

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

The proxy should preserve the talk service payload inside `data` rather than re-model every RAG field.

### `POST /api/rag/chat`

Proxies non-streaming chat to the talk service.

Request:

```json
{
  "question": "LaH10 的 Tc 和压力范围是什么？"
}
```

Validation:

- `question` must be non-empty after trimming.

Response shape:

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

The current talk service exposes this through `POST /api/chat` and returns `answer`, `chunks_used`, `citations`, `model`, `source`, optional `papers`, and optional `top10`. The SC-Wiki frontend should render `citations` as sources. SC-Wiki should not generate or alter answers; answer generation remains the talk service responsibility.

## Data Flow

```text
User opens /rag
  -> frontend calls /api/rag/health
  -> SC-Wiki backend calls talk health/API endpoint
  -> frontend shows connected or unavailable state

User searches or asks a question
  -> frontend calls /api/rag/search or /api/rag/chat
  -> SC-Wiki backend validates input
  -> SC-Wiki backend calls talk service with httpx
  -> talk service queries SQLite/Chroma/LLM
  -> SC-Wiki wraps the result
  -> frontend renders answer, result groups, or friendly error
```

## UI Design

### Home page

Add an always-visible button near existing home-page actions:

```text
🤖 AI 文献助手
```

The button links to `/rag`. It is not hidden when the talk service is unavailable; availability is explained on the `/rag` page.

### `/rag` page

The page follows existing Bootstrap styling and reuses common scripts where appropriate, including language/login-state helpers if already loaded by nearby templates.

Sections:

1. **Service status**
   - On load, call `/api/rag/health`.
   - If available, show a lightweight connected state.
   - If unavailable, show a warning alert: “AI 文献助手服务暂不可用，请稍后再试。”
   - Disable search and chat submit buttons when unavailable. Inputs remain editable.

2. **Natural-language Q&A**
   - A textarea for the question.
   - A submit button.
   - Non-streaming loading state while waiting.
   - Render the returned answer.
   - If sources/citations are present, render them below the answer.

3. **Search**
   - A single input supporting formula, element system, paper keyword, or natural language.
   - First version uses a fixed `top_k=10` to avoid unnecessary UI complexity.
   - Render result groups if present:
     - `superconductors`
     - `papers`
     - `chunks`
   - Missing groups render as empty states rather than errors.

Search and Q&A are independent. Searching does not automatically ask a question.

## Error Handling

The SC-Wiki proxy normalizes these cases:

1. **Connection failure / talk service down**
   - Health returns `available: false`.
   - Search/chat return 503 with a JSON error.

2. **Timeout**
   - Use `RAG_SERVICE_TIMEOUT`.
   - Return 504 with message: “AI 文献助手响应超时，请稍后重试”。

3. **Empty input**
   - Return 400 for empty search query or empty question.
   - The frontend also validates before submitting.

4. **Talk service non-2xx response**
   - Do not pass through an HTML error page.
   - Return a normalized JSON object:
     ```json
     {
       "ok": false,
       "message": "AI 文献助手返回错误",
       "detail": "talk service returned HTTP 500 while handling /api/chat"
     }
     ```

5. **Unexpected response shape**
   - Frontend uses defensive rendering.
   - Missing `answer`, `sources`, `superconductors`, `papers`, or `chunks` does not crash the page.

## Testing Strategy

Back-end tests should focus on the SC-Wiki proxy contract, not RAG answer quality.

Recommended backend tests:

- `GET /api/rag/health`
  - available talk service returns `available: true`.
  - unavailable talk service returns `available: false`, not 500.
- `GET /api/rag/search`
  - empty query returns 400.
  - normal proxy response returns `ok: true`.
  - connection failure returns 503.
  - timeout returns 504.
- `POST /api/rag/chat`
  - empty question returns 400.
  - normal proxy response returns `ok: true`.
  - connection failure/timeout returns expected status and message.

Manual/frontend checks:

- Home page shows “AI 文献助手” and navigates to `/rag`.
- `/rag` opens when the talk service is down and shows a disabled, friendly unavailable state.
- With the talk service running locally, search and chat render returned data.

## Implementation Notes

- Keep proxy logic small and isolated in `backend/api/rag.py`.
- Register the router in `backend/main.py` alongside existing API routers.
- Add a `frontend/templates/rag.html` page and a focused `frontend/static/js/rag.js` script.
- Avoid adding new persistent tables or migrations for the first version.
- Avoid importing `hydride_rag` from SC-Wiki; communicate over HTTP only.
