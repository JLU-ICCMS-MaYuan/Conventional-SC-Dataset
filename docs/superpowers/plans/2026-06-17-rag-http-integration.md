# RAG HTTP 集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 SC-Wiki 中通过 HTTP 代理接入 `../Conventional-SC-Dataset-talk` 的 RAG 搜索和非流式问答能力，并提供公开的 `/rag` 页面入口。

**Architecture:** SC-Wiki 新增独立后端代理模块 `backend/api/rag.py`，前端只访问 `/api/rag/*`，代理层通过 `httpx` 调用独立运行的 talk 服务。前端新增 `/rag` 页面和 `rag.js`，首页只增加入口按钮，不直接访问 talk 服务地址。

**Tech Stack:** FastAPI、httpx、Pydantic、pytest、httpx ASGITransport、Bootstrap、原生 JavaScript。

---

## 文件结构与职责

### 新增文件

- `backend/api/rag.py`
  - 单一职责：封装 SC-Wiki 到 talk 服务的 RAG HTTP 代理。
  - 对外提供 `/api/rag/health`、`/api/rag/search`、`/api/rag/chat`。
  - 负责读取 `RAG_SERVICE_URL`、`RAG_SERVICE_TIMEOUT`，并统一处理输入校验、连接失败、超时和 talk 非 2xx 响应。

- `tests/test_rag_proxy.py`
  - 单一职责：测试代理层契约，不测试 RAG 答案质量。
  - 通过 monkeypatch 替换 `backend.api.rag._request_talk_json`，避免依赖真实 talk 服务。

- `frontend/templates/rag.html`
  - 单一职责：AI 文献助手页面骨架。
  - 复用现有 Bootstrap、`i18n.js`、`auth_state.js`、`auth_helper.js`。

- `frontend/static/js/rag.js`
  - 单一职责：`/rag` 页面交互逻辑。
  - 负责健康检查、搜索、问答、loading、错误状态和防御式结果渲染。

### 修改文件

- `backend/main.py`
  - 注册 `backend.api.rag` router。
  - 新增 `/rag` 页面路由，返回 `frontend/templates/rag.html`。

- `frontend/templates/index.html`
  - 在首页现有操作按钮附近增加“🤖 AI 文献助手”入口。

---

## Task 1: 后端 RAG 代理接口

**Files:**
- Create: `backend/api/rag.py`
- Create: `tests/test_rag_proxy.py`

- [ ] **Step 1: 编写失败测试 `tests/test_rag_proxy.py`**

创建 `tests/test_rag_proxy.py`，内容如下：

```python
import anyio
import httpx
from httpx import ASGITransport, AsyncClient

from backend.main import app


def test_rag_health_available(monkeypatch):
    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/health"
        return {"status": "ok"}

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json() == {
            "available": True,
            "service_url_configured": True,
        }

    anyio.run(run)


def test_rag_health_unavailable_on_connection_error(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json()["available"] is False
        assert response.json()["service_url_configured"] is True
        assert response.json()["message"] == "AI 文献助手服务暂不可用"

    anyio.run(run)


def test_rag_search_rejects_blank_query():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "   "})
        assert response.status_code == 400
        assert response.json()["detail"] == "搜索内容不能为空"

    anyio.run(run)


def test_rag_search_proxies_success(monkeypatch):
    payload = {
        "mode": "formula",
        "query": "LaH10",
        "superconductors": [],
        "papers": [],
        "chunks": [],
        "related_paper_ids": [],
        "total": 0,
    }

    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/search"
        assert kwargs["params"] == {"q": "LaH10", "top_k": 10}
        return payload

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": " LaH10 ", "top_k": 10})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_chat_rejects_blank_question():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "  "})
        assert response.status_code == 400
        assert response.json()["detail"] == "问题不能为空"

    anyio.run(run)


def test_rag_chat_proxies_success(monkeypatch):
    payload = {
        "answer": "LaH10 的 Tc 与压力取决于具体文献记录。",
        "chunks_used": 3,
        "citations": [],
        "model": "deepseek-chat",
        "source": "rag",
        "papers": {},
        "top10": [],
    }

    async def fake_request(method, path, **kwargs):
        assert method == "POST"
        assert path == "/api/chat"
        assert kwargs["json"] == {"question": "LaH10 的 Tc？"}
        return payload

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": " LaH10 的 Tc？ "})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_search_connection_error_returns_503(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "LaH10"})
        assert response.status_code == 503
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手服务暂不可用"

    anyio.run(run)


def test_rag_chat_timeout_returns_504(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 504
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手响应超时，请稍后重试"

    anyio.run(run)


def test_rag_chat_talk_http_error_returns_502(monkeypatch):
    async def fake_request(method, path, **kwargs):
        request = httpx.Request(method, f"http://rag.local{path}")
        response = httpx.Response(500, json={"detail": "boom"}, request=request)
        raise httpx.HTTPStatusError("server error", request=request, response=response)

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 502
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手返回错误"
        assert "HTTP 500" in response.json()["detail"]["detail"]

    anyio.run(run)
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
pytest tests/test_rag_proxy.py -v
```

Expected:

```text
ERROR collecting tests/test_rag_proxy.py
ModuleNotFoundError 或 AttributeError，原因是 backend.api.rag 尚不存在或 main.py 尚未注册 rag router
```

- [ ] **Step 3: 实现 `backend/api/rag.py`**

创建 `backend/api/rag.py`，内容如下：

```python
"""RAG service proxy APIs."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/api/rag", tags=["rag"])

DEFAULT_RAG_SERVICE_URL = "http://127.0.0.1:8001"
DEFAULT_RAG_SERVICE_TIMEOUT = 30.0


def _rag_service_url() -> str:
    return os.environ.get("RAG_SERVICE_URL", DEFAULT_RAG_SERVICE_URL).rstrip("/")


def _rag_timeout() -> float:
    raw = os.environ.get("RAG_SERVICE_TIMEOUT")
    if not raw:
        return DEFAULT_RAG_SERVICE_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_RAG_SERVICE_TIMEOUT
    return value if value > 0 else DEFAULT_RAG_SERVICE_TIMEOUT


async def _request_talk_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    url = f"{_rag_service_url()}{path}"
    timeout = httpx.Timeout(_rag_timeout())
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, params=params, json=json)
        response.raise_for_status()
        return response.json()


def _service_error(status_code: int, message: str, detail: str | None = None) -> HTTPException:
    payload: dict[str, Any] = {"ok": False, "message": message}
    if detail:
        payload["detail"] = detail
    return HTTPException(status_code=status_code, detail=payload)


def _handle_proxy_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.TimeoutException):
        return _service_error(504, "AI 文献助手响应超时，请稍后重试")
    if isinstance(exc, httpx.HTTPStatusError):
        return _service_error(
            502,
            "AI 文献助手返回错误",
            f"talk service returned HTTP {exc.response.status_code} while handling {exc.request.url.path}",
        )
    if isinstance(exc, httpx.HTTPError):
        return _service_error(503, "AI 文献助手服务暂不可用")
    return _service_error(502, "AI 文献助手返回错误", str(exc))


class RagChatRequest(BaseModel):
    question: str


@router.get("/health")
async def rag_health():
    try:
        await _request_talk_json("GET", "/api/health")
    except Exception:
        return {
            "available": False,
            "service_url_configured": bool(_rag_service_url()),
            "message": "AI 文献助手服务暂不可用",
        }
    return {
        "available": True,
        "service_url_configured": bool(_rag_service_url()),
    }


@router.get("/search")
async def rag_search(
    q: str = Query(...),
    top_k: int = Query(10, ge=1, le=20),
):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    try:
        data = await _request_talk_json(
            "GET",
            "/api/search",
            params={"q": query, "top_k": top_k},
        )
    except Exception as exc:
        raise _handle_proxy_error(exc) from exc
    return {"ok": True, "data": data}


@router.post("/chat")
async def rag_chat(request: RagChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    try:
        data = await _request_talk_json(
            "POST",
            "/api/chat",
            json={"question": question},
        )
    except Exception as exc:
        raise _handle_proxy_error(exc) from exc
    return {"ok": True, "data": data}
```

- [ ] **Step 4: 在 `backend/main.py` 注册 router**

修改导入行：

```python
from backend.api import elements, compounds, papers, admin, auth_routes, tc_predict, alexandria, htsc2025, structures, rag
```

在现有 router 注册区域添加：

```python
app.include_router(rag.router)  # RAG 代理 API
```

推荐放在 `structures.router` 后面。

- [ ] **Step 5: 运行后端代理测试，确认通过**

Run:

```bash
pytest tests/test_rag_proxy.py -v
```

Expected:

```text
9 passed
```

- [ ] **Step 6: 提交后端代理接口**

```bash
git add backend/api/rag.py backend/main.py tests/test_rag_proxy.py
git commit -m "feat: add rag service proxy api"
```

---

## Task 2: `/rag` 页面路由和首页入口

**Files:**
- Modify: `backend/main.py`
- Modify: `frontend/templates/index.html`
- Test: `tests/test_rag_page.py`

- [ ] **Step 1: 编写失败测试 `tests/test_rag_page.py`**

创建 `tests/test_rag_page.py`，内容如下：

```python
import anyio
from httpx import ASGITransport, AsyncClient

from backend.main import app


def test_rag_page_route_returns_html():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/rag")
        assert response.status_code == 200
        assert "AI 文献助手" in response.text
        assert "/static/js/rag.js" in response.text

    anyio.run(run)
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
pytest tests/test_rag_page.py -v
```

Expected:

```text
FAILED tests/test_rag_page.py::test_rag_page_route_returns_html
assert 404 == 200 或页面文件不存在
```

- [ ] **Step 3: 在 `backend/main.py` 新增 `/rag` 页面路由**

在 `tc_prediction_page()` 后、健康检查端点前添加：

```python
@app.get("/rag")
def rag_page():
    """AI 文献助手页面"""
    page_file = TEMPLATES_DIR / "rag.html"
    if page_file.exists():
        return FileResponse(page_file)
    return {"error": "页面不存在"}
```

- [ ] **Step 4: 在首页添加入口按钮**

修改 `frontend/templates/index.html` 中现有按钮区域。找到：

```html
<a class="btn btn-outline-warning ms-1" href="/tc-pre" data-i18n="index.tc_predict_lab">⚡ 超导预测实验</a>
<input type="file" id="fast-upload-input" style="display: none;" accept=".xlsx,.csv,.txt" onchange="handleFastUpload(this)">
```

替换为：

```html
<a class="btn btn-outline-warning ms-1" href="/tc-pre" data-i18n="index.tc_predict_lab">⚡ 超导预测实验</a>
<a class="btn btn-outline-primary ms-1" href="/rag">🤖 AI 文献助手</a>
<input type="file" id="fast-upload-input" style="display: none;" accept=".xlsx,.csv,.txt" onchange="handleFastUpload(this)">
```

- [ ] **Step 5: 运行页面路由测试，确认仍因模板缺失失败**

Run:

```bash
pytest tests/test_rag_page.py -v
```

Expected:

```text
FAILED tests/test_rag_page.py::test_rag_page_route_returns_html
响应中不包含 AI 文献助手 或 /static/js/rag.js，因为 rag.html 尚未创建
```

此失败是预期的，下一任务创建页面模板。

- [ ] **Step 6: 提交路由和首页入口**

```bash
git add backend/main.py frontend/templates/index.html tests/test_rag_page.py
git commit -m "feat: add rag page route and home entry"
```

---

## Task 3: `/rag` 页面模板

**Files:**
- Create: `frontend/templates/rag.html`
- Test: `tests/test_rag_page.py`

- [ ] **Step 1: 创建 `frontend/templates/rag.html`**

创建文件，内容如下：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 文献助手 - 超导文献数据库</title>
    <link href="/static/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-custom shadow-sm sticky-top">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="/">超导文献数据库</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item"><a class="nav-link" href="/">首页</a></li>
                    <li class="nav-item"><a class="nav-link active" href="/rag">AI 文献助手</a></li>
                    <li class="nav-item"><a class="nav-link" href="/tc-pre">Tc 预测 (实验)</a></li>
                </ul>
                <div class="d-flex align-items-center gap-2" id="user-nav">
                    <div class="spinner-border spinner-border-sm text-light" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                <button class="btn btn-outline-light btn-sm ms-2" onclick="I18N.toggle()" title="Switch Language">中/EN</button>
            </div>
        </div>
    </nav>

    <main class="container py-4">
        <header class="mb-4">
            <h1 class="fw-bold">🤖 AI 文献助手</h1>
            <p class="text-muted mb-0">基于氢化物超导文献 RAG 系统，提供文献搜索和非流式问答。</p>
        </header>

        <section id="rag-status" class="alert alert-secondary" role="status">
            正在检查 AI 文献助手服务状态...
        </section>

        <div class="row g-4">
            <section class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-light">
                        <h2 class="h5 mb-0">自然语言问答</h2>
                    </div>
                    <div class="card-body">
                        <label for="rag-question" class="form-label">问题</label>
                        <textarea id="rag-question" class="form-control" rows="5" placeholder="例如：LaH10 的 Tc 和压力范围是什么？"></textarea>
                        <button id="rag-chat-submit" class="btn btn-primary mt-3" type="button">提问</button>
                        <div id="rag-chat-error" class="alert alert-danger mt-3 d-none"></div>
                        <div id="rag-chat-result" class="mt-3"></div>
                    </div>
                </div>
            </section>

            <section class="col-lg-6">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-light">
                        <h2 class="h5 mb-0">文献 / 材料搜索</h2>
                    </div>
                    <div class="card-body">
                        <label for="rag-search-query" class="form-label">搜索内容</label>
                        <input id="rag-search-query" class="form-control" type="text" placeholder="例如：LaH10、La-H、hydride superconductors">
                        <button id="rag-search-submit" class="btn btn-outline-primary mt-3" type="button">搜索</button>
                        <div id="rag-search-error" class="alert alert-danger mt-3 d-none"></div>
                        <div id="rag-search-result" class="mt-3"></div>
                    </div>
                </div>
            </section>
        </div>
    </main>

    <script src="/static/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/i18n.js"></script>
    <script src="/static/js/auth_state.js"></script>
    <script src="/static/js/auth_helper.js"></script>
    <script src="/static/js/rag.js"></script>
</body>
</html>
```

- [ ] **Step 2: 运行页面测试，确认通过**

Run:

```bash
pytest tests/test_rag_page.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 3: 提交页面模板**

```bash
git add frontend/templates/rag.html tests/test_rag_page.py
git commit -m "feat: add rag assistant page template"
```

---

## Task 4: `/rag` 页面前端交互脚本

**Files:**
- Create: `frontend/static/js/rag.js`

- [ ] **Step 1: 创建 `frontend/static/js/rag.js`**

创建文件，内容如下：

```javascript
function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
}

function setAlert(el, type, message) {
    el.className = `alert alert-${type}`;
    el.textContent = message;
    el.classList.remove('d-none');
}

function clearAlert(el) {
    el.textContent = '';
    el.classList.add('d-none');
}

function setControlsEnabled(enabled) {
    document.getElementById('rag-chat-submit').disabled = !enabled;
    document.getElementById('rag-search-submit').disabled = !enabled;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = data.detail || data;
        const message = detail.message || detail.detail || data.message || `请求失败：HTTP ${response.status}`;
        throw new Error(message);
    }
    return data;
}

async function checkRagHealth() {
    const statusEl = document.getElementById('rag-status');
    setControlsEnabled(false);
    try {
        const payload = await fetchJson('/api/rag/health');
        if (payload.available) {
            setAlert(statusEl, 'success', 'AI 文献助手已连接。');
            setControlsEnabled(true);
        } else {
            setAlert(statusEl, 'warning', payload.message || 'AI 文献助手服务暂不可用，请稍后再试。');
            setControlsEnabled(false);
        }
    } catch (error) {
        setAlert(statusEl, 'warning', `AI 文献助手服务暂不可用：${error.message}`);
        setControlsEnabled(false);
    }
}

function renderCitations(citations) {
    if (!Array.isArray(citations) || citations.length === 0) {
        return '';
    }
    const items = citations.map((item) => {
        const title = item.title || item.paper_title || item.doi || item.id || '来源';
        return `<li>${escapeHtml(title)}</li>`;
    }).join('');
    return `<h3 class="h6 mt-3">来源</h3><ul>${items}</ul>`;
}

async function submitChat() {
    const questionEl = document.getElementById('rag-question');
    const errorEl = document.getElementById('rag-chat-error');
    const resultEl = document.getElementById('rag-chat-result');
    const button = document.getElementById('rag-chat-submit');
    const question = questionEl.value.trim();

    clearAlert(errorEl);
    if (!question) {
        setAlert(errorEl, 'danger', '问题不能为空');
        return;
    }

    button.disabled = true;
    resultEl.innerHTML = '<div class="text-muted">正在生成回答...</div>';
    try {
        const payload = await fetchJson('/api/rag/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question}),
        });
        const data = payload.data || {};
        const answer = data.answer || 'AI 文献助手未返回答案。';
        resultEl.innerHTML = `
            <div class="border rounded p-3 bg-light">
                <div style="white-space: pre-wrap;">${escapeHtml(answer)}</div>
                ${renderCitations(data.citations || data.sources)}
            </div>
        `;
    } catch (error) {
        resultEl.innerHTML = '';
        setAlert(errorEl, 'danger', error.message);
    } finally {
        button.disabled = false;
    }
}

function renderList(title, items, formatter) {
    if (!Array.isArray(items) || items.length === 0) {
        return `<section class="mb-3"><h3 class="h6">${escapeHtml(title)}</h3><p class="text-muted mb-0">暂无结果</p></section>`;
    }
    return `
        <section class="mb-3">
            <h3 class="h6">${escapeHtml(title)}</h3>
            <div class="list-group">
                ${items.map(formatter).join('')}
            </div>
        </section>
    `;
}

function renderSearchResults(data) {
    return [
        renderList('超导体', data.superconductors, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.chemical_formula || item.display_name || item.formula_normalized || '未知材料')}</strong>
                <div class="small text-muted">${escapeHtml(item.formula_normalized || '')}</div>
            </div>
        `),
        renderList('论文', data.papers, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.title || item.doi || '未知论文')}</strong>
                <div class="small text-muted">${escapeHtml([item.journal, item.year].filter(Boolean).join(' · '))}</div>
            </div>
        `),
        renderList('文本片段', data.chunks, (item) => `
            <div class="list-group-item">
                <div>${escapeHtml(item.content || item.text || item.chunk || '无文本内容')}</div>
                <div class="small text-muted">paper_id: ${escapeHtml(item.paper_id || '-')}</div>
            </div>
        `),
    ].join('');
}

async function submitSearch() {
    const queryEl = document.getElementById('rag-search-query');
    const errorEl = document.getElementById('rag-search-error');
    const resultEl = document.getElementById('rag-search-result');
    const button = document.getElementById('rag-search-submit');
    const query = queryEl.value.trim();

    clearAlert(errorEl);
    if (!query) {
        setAlert(errorEl, 'danger', '搜索内容不能为空');
        return;
    }

    button.disabled = true;
    resultEl.innerHTML = '<div class="text-muted">正在搜索...</div>';
    try {
        const params = new URLSearchParams({q: query, top_k: '10'});
        const payload = await fetchJson(`/api/rag/search?${params.toString()}`);
        const data = payload.data || {};
        resultEl.innerHTML = renderSearchResults(data);
    } catch (error) {
        resultEl.innerHTML = '';
        setAlert(errorEl, 'danger', error.message);
    } finally {
        button.disabled = false;
    }
}

function initRagPage() {
    document.getElementById('rag-chat-submit').addEventListener('click', submitChat);
    document.getElementById('rag-search-submit').addEventListener('click', submitSearch);
    document.getElementById('rag-search-query').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitSearch();
        }
    });
    checkRagHealth();
}

document.addEventListener('DOMContentLoaded', initRagPage);
```

- [ ] **Step 2: 运行页面路由测试，确认静态脚本引用有效**

Run:

```bash
pytest tests/test_rag_page.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 3: 提交前端交互脚本**

```bash
git add frontend/static/js/rag.js frontend/templates/rag.html
git commit -m "feat: add rag assistant page interactions"
```

---

## Task 5: 集成测试与手动验证

**Files:**
- Modify: `docs/superpowers/plans/2026-06-17-rag-http-integration.md` only if verification notes need correction before execution starts; otherwise no code changes.

- [ ] **Step 1: 运行 RAG 相关测试**

Run:

```bash
pytest tests/test_rag_proxy.py tests/test_rag_page.py -v
```

Expected:

```text
10 passed
```

如果数量不同，以实际测试数量为准，但必须全部通过。

- [ ] **Step 2: 运行现有相关测试，确认未破坏主应用导入**

Run:

```bash
pytest tests/test_structures_api.py tests/test_superconductor_repository.py -v
```

Expected:

```text
所有测试通过
```

如果失败，先确认失败是否来自本次变更。不能把失败测试标记为完成。

- [ ] **Step 3: 启动 talk 服务用于手动验证**

在相邻项目中运行：

```bash
cd ../Conventional-SC-Dataset-talk
uvicorn hydride_rag.api.app:app --host 0.0.0.0 --port 8001
```

Expected:

```text
Uvicorn running on http://0.0.0.0:8001
```

- [ ] **Step 4: 启动 SC-Wiki 服务**

在 SC-Wiki 项目根目录运行：

```bash
RAG_SERVICE_URL=http://127.0.0.1:8001 uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected:

```text
Uvicorn running on http://0.0.0.0:8000
```

- [ ] **Step 5: 手动检查服务不可用降级**

停止 talk 服务，仅保留 SC-Wiki 服务。打开：

```text
http://localhost:8000/rag
```

Expected:

```text
页面正常打开，状态提示“AI 文献助手服务暂不可用”，搜索和提问按钮禁用。
```

- [ ] **Step 6: 手动检查服务可用路径**

重新启动 talk 服务，刷新：

```text
http://localhost:8000/rag
```

Expected:

```text
状态提示“AI 文献助手已连接。”
```

在搜索框输入：

```text
LaH10
```

点击“搜索”。Expected:

```text
页面展示超导体、论文或文本片段分组；没有结果时显示“暂无结果”，页面不报错。
```

在问答框输入：

```text
LaH10 的 Tc 和压力范围是什么？
```

点击“提问”。Expected:

```text
页面展示 AI 返回答案；如果返回 citations，则显示来源列表。
```

- [ ] **Step 7: 提交最终验证修正**

如果 Task 5 期间没有代码修正，则不需要提交。

如果有修正，执行：

```bash
git add backend/api/rag.py backend/main.py frontend/templates/index.html frontend/templates/rag.html frontend/static/js/rag.js tests/test_rag_proxy.py tests/test_rag_page.py
git commit -m "fix: stabilize rag integration"
```

---

## 自检结果

- **Spec 覆盖：**
  - 首页入口：Task 2。
  - `/rag` 页面：Task 2、Task 3、Task 4。
  - `/api/rag/health`、`/api/rag/search`、`/api/rag/chat`：Task 1。
  - HTTP 松耦合代理、`RAG_SERVICE_URL`、`RAG_SERVICE_TIMEOUT`：Task 1。
  - 非流式问答：Task 1、Task 4。
  - 友好降级、503、504、非 2xx 归一：Task 1、Task 4、Task 5。
  - 不持久化、不合并代码、不直接连接 Chroma/SQLite：Task 1 的实现边界满足。

- **占位符扫描：**计划中没有 `TBD`、`TODO`、`待定`、`implement later` 或未定义函数名。

- **类型一致性：**
  - 后端代理函数统一为 `_request_talk_json(method, path, params=None, json=None)`。
  - 前端 API 统一使用 `/api/rag/health`、`/api/rag/search`、`/api/rag/chat`。
  - talk chat 返回字段按 spec 使用 `answer`、`chunks_used`、`citations`、`model`、`source`、`papers`、`top10`。
