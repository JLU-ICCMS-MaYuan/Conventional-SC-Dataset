# RAG 代码级同进程集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `../Conventional-SC-Dataset-talk` 的 RAG 搜索和非流式问答能力迁入 SC-Wiki，使 `/api/rag/*` 在同一个 SC-Wiki 进程内工作，不再依赖 talk uvicorn 服务。

**Architecture:** 在 SC-Wiki 新增 `backend/rag/` 内部子系统，迁入 talk 项目的运行时 RAG 模块并把 import 从 `hydride_rag` 改为 `backend.rag`。`backend/api/rag.py` 保持前端 API 契约不变，但从 HTTP 代理改为调用 `backend.rag.service`。RAG 数据仍读取相邻 `../Conventional-SC-Dataset-talk/dev.db` 和 `../Conventional-SC-Dataset-talk/chroma_db`。

**Tech Stack:** FastAPI、SQLAlchemy asyncio、aiosqlite、ChromaDB、OpenAI SDK / DeepSeek compatible API、Pydantic Settings、pytest、原生 JavaScript。

---

## 当前约束

- 当前 `rag` 工作区有用户恢复的未提交改动。实施时只触碰本计划列出的文件。
- 不复制 `dev.db`、`chroma_db` 或 talk 项目的 ingest/api 目录。
- 不删除当前已实现的 `/rag` 页面；只改 API 后端和少量 health 前端状态逻辑。
- 每个任务完成后只提交本任务相关文件。

## 文件结构与职责

### 新增文件/目录

- `backend/rag/`
  - 从 `../Conventional-SC-Dataset-talk/src/hydride_rag` 迁入运行时模块。
  - 包含 `config.py`、`database.py`、`vectordb.py`、`knowledge_graph.py`、`models/`、`search/`、`rag/`。

- `backend/rag/service.py`
  - SC-Wiki 内部稳定门面。
  - 对 API 层暴露：`health()`、`search(query, top_k)`、`chat(question)`。
  - 定义：`RagDataUnavailableError`、`RagChatUnavailableError`、`RagInternalError`。

- `tests/test_rag_internal_imports.py`
  - 验证迁移后的 import 可用，且不依赖顶层 `hydride_rag` 包。

- `tests/test_rag_internal_api.py`
  - 验证 `/api/rag/*` 改为内部调用后的 API 契约和错误映射。

### 修改文件

- `backend/api/rag.py`
  - 移除 `httpx` 外部代理逻辑。
  - 改为调用 `backend.rag.service`。

- `frontend/static/js/rag.js`
  - 增强 health 状态：搜索可用但 LLM 未配置时，只禁用提问按钮。

- `requirements.txt`
  - 增加 RAG 运行时依赖：`aiosqlite`、`asyncmy`、`openai`、`chromadb`。

---

## Task 1: 迁移 RAG 运行时代码骨架并修正 import

**Files:**
- Create: `backend/rag/**`
- Test: `tests/test_rag_internal_imports.py`

- [ ] **Step 1: 编写失败测试 `tests/test_rag_internal_imports.py`**

创建文件：

```python
import importlib


def test_internal_rag_runtime_imports():
    modules = [
        "backend.rag.config",
        "backend.rag.database",
        "backend.rag.vectordb",
        "backend.rag.search.engine",
        "backend.rag.rag.engine",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert module is not None


def test_internal_rag_public_functions_importable():
    from backend.rag.config import get_rag_settings
    from backend.rag.search.engine import search
    from backend.rag.rag.engine import ask

    settings = get_rag_settings()
    assert settings.rag_data_root.name == "Conventional-SC-Dataset-talk"
    assert callable(search)
    assert callable(ask)
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_imports.py -v
```

Expected:

```text
FAILED 或 ERROR: ModuleNotFoundError: No module named 'backend.rag'
```

- [ ] **Step 3: 复制 talk 运行时源码到 `backend/rag/`**

Run:

```bash
mkdir -p backend/rag
rsync -a \
  --exclude '__pycache__' \
  --exclude 'api' \
  --exclude 'ingest' \
  ../Conventional-SC-Dataset-talk/src/hydride_rag/ \
  backend/rag/
```

复制后确认：

```bash
find backend/rag -maxdepth 2 -type f | sort
```

Expected includes:

```text
backend/rag/config.py
backend/rag/database.py
backend/rag/vectordb.py
backend/rag/knowledge_graph.py
backend/rag/models/paper.py
backend/rag/search/engine.py
backend/rag/rag/engine.py
```

- [ ] **Step 4: 全局替换 import 包名**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('backend/rag').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    text = text.replace('from hydride_rag.', 'from backend.rag.')
    text = text.replace('import hydride_rag.', 'import backend.rag.')
    text = text.replace('import hydride_rag.models', 'import backend.rag.models')
    path.write_text(text, encoding='utf-8')
PY
```

- [ ] **Step 5: 替换 `backend/rag/config.py` 为 SC-Wiki 路径感知配置**

将 `backend/rag/config.py` 完整替换为：

```python
"""SC-Wiki internal RAG configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    rag_data_root: Path | None = None
    rag_database_url: str | None = None
    rag_chroma_path: Path | None = None

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def data_root(self) -> Path:
        if self.rag_data_root is not None:
            return self.rag_data_root.expanduser().resolve()
        env_root = os.environ.get("RAG_DATA_ROOT")
        if env_root:
            return Path(env_root).expanduser().resolve()
        return (Path(__file__).resolve().parents[3] / "Conventional-SC-Dataset-talk").resolve()

    @property
    def database_url(self) -> str:
        if self.rag_database_url:
            return self.rag_database_url
        db_path = self.data_root / "dev.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def chroma_path(self) -> Path:
        if self.rag_chroma_path is not None:
            return self.rag_chroma_path.expanduser().resolve()
        env_path = os.environ.get("RAG_CHROMA_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()
        return self.data_root / "chroma_db"

    @property
    def chat_configured(self) -> bool:
        return bool(self.deepseek_api_key)


@lru_cache(maxsize=1)
def get_rag_settings() -> RagSettings:
    return RagSettings()


settings = get_rag_settings()
```

- [ ] **Step 6: 修正 `backend/rag/database.py` 使用新配置属性**

把文件中的 `settings.database_url` 替换为 `settings.database_url` 后无需改名，因为新配置保留了同名 property。确保文件顶部 import 是：

```python
from backend.rag.config import settings
```

确保 `init_db()` 内部 import 是：

```python
import backend.rag.models  # noqa: F401
```

- [ ] **Step 7: 修正 `backend/rag/vectordb.py` 使用 RAG Chroma 路径且不自动创建目录**

把顶部 Chroma 路径部分改为：

```python
from backend.rag.config import settings as rag_settings

CHROMA_DIR = rag_settings.chroma_path
```

删除或不要保留：

```python
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 8: 运行 import 测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_imports.py -v
```

Expected:

```text
2 passed
```

如果失败显示缺少依赖，例如 `ModuleNotFoundError: No module named 'chromadb'` 或 `No module named 'openai'`，先执行 Task 2。

- [ ] **Step 9: 提交迁移骨架**

```bash
git add backend/rag tests/test_rag_internal_imports.py
git commit -m "feat: add internal rag runtime modules"
```

---

## Task 2: 补齐 RAG 运行时依赖

**Files:**
- Modify: `requirements.txt`
- Test: `tests/test_rag_internal_imports.py`

- [ ] **Step 1: 修改 `requirements.txt`**

在 `httpx==0.26.0` 后添加：

```text
openai>=1.0
chromadb>=0.5
aiosqlite>=0.20
asyncmy>=0.2
```

修改后相关片段应为：

```text
# HTTP客户端
httpx==0.26.0
openai>=1.0
chromadb>=0.5
aiosqlite>=0.20
asyncmy>=0.2
```

- [ ] **Step 2: 在项目 conda 环境安装新增依赖**

Run:

```bash
conda run -n Conventional-SC-Dataset python -m pip install "openai>=1.0" "chromadb>=0.5" "aiosqlite>=0.20" "asyncmy>=0.2"
```

Expected:

```text
Successfully installed ...
```

- [ ] **Step 3: 运行 import 测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_imports.py -v
```

Expected:

```text
2 passed
```

- [ ] **Step 4: 提交依赖声明**

```bash
git add requirements.txt
git commit -m "chore: add internal rag runtime dependencies"
```

---

## Task 3: 新增内部 RAG service 门面

**Files:**
- Create: `backend/rag/service.py`
- Test: `tests/test_rag_service.py`

- [ ] **Step 1: 编写 `tests/test_rag_service.py`**

创建文件：

```python
from pathlib import Path

import pytest

from backend.rag.config import get_rag_settings
from backend.rag import service


def test_health_reports_missing_data(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATA_ROOT", str(tmp_path / "missing-talk"))
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is False
    assert status["database_available"] is False
    assert status["chroma_available"] is False
    assert status["chat_available"] is False
    assert status["message"] == "AI 文献助手数据不可用"


def test_health_reports_search_available_without_llm(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True
    assert status["chat_available"] is False
    assert status["message"] == "RAG 检索可用，LLM 问答未配置"


@pytest.mark.asyncio
async def test_search_raises_when_data_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATA_ROOT", str(tmp_path / "missing-talk"))
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagDataUnavailableError):
        await service.search("LaH10", top_k=3)


@pytest.mark.asyncio
async def test_chat_raises_when_llm_missing(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagChatUnavailableError):
        await service.chat("LaH10 的 Tc？")
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_service.py -v
```

Expected:

```text
ERROR 或 FAILED: cannot import name 'service' from 'backend.rag'
```

- [ ] **Step 3: 创建 `backend/rag/service.py`**

内容：

```python
"""Stable service facade for SC-Wiki internal RAG APIs."""

from __future__ import annotations

from typing import Any

from backend.rag.config import get_rag_settings


class RagDataUnavailableError(RuntimeError):
    """Raised when the RAG SQLite/Chroma data files are unavailable."""


class RagChatUnavailableError(RuntimeError):
    """Raised when LLM-backed chat is not configured."""


class RagInternalError(RuntimeError):
    """Raised when the internal RAG runtime fails unexpectedly."""


def health() -> dict[str, Any]:
    settings = get_rag_settings()
    db_url = settings.database_url
    db_path_text = db_url.replace("sqlite+aiosqlite:///", "", 1)
    db_path = settings.data_root / "dev.db" if db_path_text == db_url else __import__("pathlib").Path(db_path_text)
    database_available = db_path.exists()
    chroma_available = settings.chroma_path.exists()
    chat_available = settings.chat_configured
    available = database_available and chroma_available

    if not available:
        message = "AI 文献助手数据不可用"
    elif not chat_available:
        message = "RAG 检索可用，LLM 问答未配置"
    else:
        message = "AI 文献助手已就绪"

    return {
        "available": available,
        "database_available": database_available,
        "chroma_available": chroma_available,
        "chat_available": chat_available,
        "message": message,
    }


def _ensure_data_available() -> None:
    status = health()
    if not status["available"]:
        raise RagDataUnavailableError("AI 文献助手数据不可用")


async def search(query: str, top_k: int = 10) -> dict[str, Any]:
    _ensure_data_available()
    try:
        from backend.rag.search.engine import search as rag_search
        return await rag_search(query, top_k=top_k)
    except RagDataUnavailableError:
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def chat(question: str) -> dict[str, Any]:
    _ensure_data_available()
    if not get_rag_settings().chat_configured:
        raise RagChatUnavailableError("LLM 问答未配置")
    try:
        from backend.rag.rag.engine import ask
        return await ask(question)
    except RagChatUnavailableError:
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc
```

- [ ] **Step 4: 运行 service 测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_service.py -v
```

Expected:

```text
4 passed
```

- [ ] **Step 5: 提交 service 门面**

```bash
git add backend/rag/service.py tests/test_rag_service.py
git commit -m "feat: add internal rag service facade"
```

---

## Task 4: 改造 `/api/rag/*` 从 HTTP 代理为内部调用

**Files:**
- Modify: `backend/api/rag.py`
- Create: `tests/test_rag_internal_api.py`
- Existing test may remain: `tests/test_rag_proxy.py` should be replaced or removed if it only tests HTTP proxy behavior.

- [ ] **Step 1: 编写内部 API 测试 `tests/test_rag_internal_api.py`**

创建文件：

```python
import anyio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.rag import service


def test_rag_health_uses_internal_service(monkeypatch):
    monkeypatch.setattr(service, "health", lambda: {
        "available": True,
        "database_available": True,
        "chroma_available": True,
        "chat_available": False,
        "message": "RAG 检索可用，LLM 问答未配置",
    })

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["chat_available"] is False
        assert response.json()["message"] == "RAG 检索可用，LLM 问答未配置"

    anyio.run(run)


def test_rag_search_internal_success(monkeypatch):
    payload = {"mode": "formula", "query": "LaH10", "superconductors": [], "chunks": [], "papers": [], "total": 0}

    async def fake_search(query, top_k=10):
        assert query == "LaH10"
        assert top_k == 10
        return payload

    monkeypatch.setattr(service, "search", fake_search)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": " LaH10 ", "top_k": 10})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_search_data_unavailable(monkeypatch):
    async def fake_search(query, top_k=10):
        raise service.RagDataUnavailableError("AI 文献助手数据不可用")

    monkeypatch.setattr(service, "search", fake_search)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "LaH10"})
        assert response.status_code == 503
        assert response.json()["detail"]["message"] == "AI 文献助手数据不可用"

    anyio.run(run)


def test_rag_chat_internal_success(monkeypatch):
    payload = {"answer": "ok", "chunks_used": 0, "citations": [], "model": "deepseek-chat", "source": "rag"}

    async def fake_chat(question):
        assert question == "LaH10 的 Tc？"
        return payload

    monkeypatch.setattr(service, "chat", fake_chat)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": " LaH10 的 Tc？ "})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_chat_llm_unconfigured(monkeypatch):
    async def fake_chat(question):
        raise service.RagChatUnavailableError("LLM 问答未配置")

    monkeypatch.setattr(service, "chat", fake_chat)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 503
        assert response.json()["detail"]["message"] == "LLM 问答未配置"

    anyio.run(run)
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_api.py -v
```

Expected:

```text
FAILED，因为 backend/api/rag.py 仍调用 _request_talk_json HTTP 代理
```

- [ ] **Step 3: 替换 `backend/api/rag.py` 为内部调用版**

将文件完整替换为：

```python
"""Internal RAG APIs for SC-Wiki."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.rag import service


router = APIRouter(prefix="/api/rag", tags=["rag"])


class RagChatRequest(BaseModel):
    question: str


def _service_error(status_code: int, message: str, detail: str | None = None) -> HTTPException:
    payload: dict[str, Any] = {"ok": False, "message": message}
    if detail:
        payload["detail"] = detail
    return HTTPException(status_code=status_code, detail=payload)


def _map_internal_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.RagDataUnavailableError):
        return _service_error(503, "AI 文献助手数据不可用")
    if isinstance(exc, service.RagChatUnavailableError):
        return _service_error(503, "LLM 问答未配置")
    if isinstance(exc, service.RagInternalError):
        return _service_error(502, "AI 文献助手返回错误", str(exc))
    return _service_error(502, "AI 文献助手返回错误", str(exc))


@router.get("/health")
async def rag_health():
    return service.health()


@router.get("/search")
async def rag_search(
    q: str = Query(...),
    top_k: int = Query(10, ge=1, le=20),
):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    try:
        data = await service.search(query, top_k=top_k)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.post("/chat")
async def rag_chat(request: RagChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    try:
        data = await service.chat(question)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}
```

- [ ] **Step 4: 运行内部 API 测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_api.py -v
```

Expected:

```text
5 passed
```

- [ ] **Step 5: 处理旧 HTTP 代理测试**

`tests/test_rag_proxy.py` 测的是旧 `_request_talk_json` 行为。删除该文件：

```bash
git rm tests/test_rag_proxy.py
```

- [ ] **Step 6: 提交 API 改造**

```bash
git add backend/api/rag.py tests/test_rag_internal_api.py
git rm --cached tests/test_rag_proxy.py 2>/dev/null || true
git add -u tests/test_rag_proxy.py
git commit -m "feat: use internal rag service in api"
```

---

## Task 5: 增强 `/rag` 页面 health 状态处理

**Files:**
- Modify: `frontend/static/js/rag.js`
- Test: `tests/test_rag_page.py`

- [ ] **Step 1: 增加页面测试断言**

修改 `tests/test_rag_page.py`，确保页面仍加载 `rag.js`。文件应保持：

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

- [ ] **Step 2: 修改 `frontend/static/js/rag.js` 的控制按钮逻辑**

将：

```javascript
function setControlsEnabled(enabled) {
    document.getElementById('rag-chat-submit').disabled = !enabled;
    document.getElementById('rag-search-submit').disabled = !enabled;
}
```

替换为：

```javascript
function setControlsEnabled(searchEnabled, chatEnabled = searchEnabled) {
    document.getElementById('rag-search-submit').disabled = !searchEnabled;
    document.getElementById('rag-chat-submit').disabled = !chatEnabled;
}
```

将 `checkRagHealth()` 替换为：

```javascript
async function checkRagHealth() {
    const statusEl = document.getElementById('rag-status');
    setControlsEnabled(false, false);
    try {
        const payload = await fetchJson('/api/rag/health');
        if (!payload.available) {
            setAlert(statusEl, 'warning', payload.message || 'AI 文献助手数据不可用');
            setControlsEnabled(false, false);
            return;
        }
        if (payload.chat_available === false) {
            setAlert(statusEl, 'warning', payload.message || 'RAG 检索可用，LLM 问答未配置');
            setControlsEnabled(true, false);
            return;
        }
        setAlert(statusEl, 'success', payload.message || 'AI 文献助手已就绪');
        setControlsEnabled(true, true);
    } catch (error) {
        setAlert(statusEl, 'warning', `AI 文献助手数据不可用：${error.message}`);
        setControlsEnabled(false, false);
    }
}
```

- [ ] **Step 3: 运行页面测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest tests/test_rag_page.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 4: 提交前端 health 处理**

```bash
git add frontend/static/js/rag.js tests/test_rag_page.py
git commit -m "feat: reflect internal rag health state in ui"
```

---

## Task 6: 轻量真实集成测试与最终验证

**Files:**
- Create: `tests/test_rag_internal_real.py`

- [ ] **Step 1: 编写轻量真实集成测试**

创建 `tests/test_rag_internal_real.py`：

```python
from pathlib import Path

import pytest

from backend.rag import service


DATA_ROOT = Path(__file__).resolve().parents[1].parent / "Conventional-SC-Dataset-talk"
DEV_DB = DATA_ROOT / "dev.db"
CHROMA_DIR = DATA_ROOT / "chroma_db"


@pytest.mark.skipif(not DEV_DB.exists() or not CHROMA_DIR.exists(), reason="RAG data not available")
def test_real_rag_health_detects_adjacent_data(monkeypatch):
    monkeypatch.setenv("RAG_DATA_ROOT", str(DATA_ROOT))
    from backend.rag.config import get_rag_settings
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True


@pytest.mark.skipif(not DEV_DB.exists() or not CHROMA_DIR.exists(), reason="RAG data not available")
@pytest.mark.asyncio
async def test_real_rag_search_returns_standard_shape(monkeypatch):
    monkeypatch.setenv("RAG_DATA_ROOT", str(DATA_ROOT))
    from backend.rag.config import get_rag_settings
    get_rag_settings.cache_clear()

    result = await service.search("LaH10", top_k=3)

    assert result["query"] == "LaH10"
    assert "mode" in result
    assert "superconductors" in result
    assert "chunks" in result
    assert "papers" in result
    assert "total" in result
```

- [ ] **Step 2: 运行 RAG 内部测试集**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest \
  tests/test_rag_internal_imports.py \
  tests/test_rag_service.py \
  tests/test_rag_internal_api.py \
  tests/test_rag_internal_real.py \
  tests/test_rag_page.py \
  -v
```

Expected:

```text
所有测试 passed；如果相邻数据不存在，tests/test_rag_internal_real.py 中真实测试 skipped
```

- [ ] **Step 3: 运行既有相关测试**

Run:

```bash
PYTHONPATH=. conda run -n Conventional-SC-Dataset pytest \
  tests/test_structures_api.py \
  tests/test_superconductor_repository.py \
  -v
```

Expected:

```text
所有测试 passed
```

- [ ] **Step 4: 手动启动 SC-Wiki，不启动 talk 服务**

Run:

```bash
PYTHONPATH=. \
DATABASE_URL="sqlite:////home/work/workshop/git/SC-Wiki/data/dev.db" \
conda run -n Conventional-SC-Dataset \
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8010
```

- [ ] **Step 5: 手动验证内部 RAG API**

Run:

```bash
curl http://127.0.0.1:8010/api/rag/health
curl "http://127.0.0.1:8010/api/rag/search?q=LaH10&top_k=3"
```

Expected health when LLM is not configured:

```json
{"available":true,"database_available":true,"chroma_available":true,"chat_available":false,"message":"RAG 检索可用，LLM 问答未配置"}
```

Expected search:

```json
{"ok":true,"data":{"mode":"...","query":"LaH10",...}}
```

- [ ] **Step 6: 提交真实集成测试**

```bash
git add tests/test_rag_internal_real.py
git commit -m "test: add internal rag integration smoke tests"
```

---

## 自检结果

- **Spec 覆盖：**
  - 代码迁入 `backend/rag/`：Task 1。
  - 不复制数据，只读相邻 `dev.db`/`chroma_db`：Task 1、Task 3、Task 6。
  - API 从 HTTP 代理切到内部调用：Task 4。
  - 搜索可用、问答需 `DEEPSEEK_API_KEY`：Task 3、Task 4、Task 5。
  - 前端 health 状态增强：Task 5。
  - import、API、真实轻量测试：Task 1、Task 4、Task 6。

- **占位符扫描：**计划没有 `TBD`、`TODO`、`待定` 或未定义函数；示例中的省略只用于 JSON 预期说明，不是实现占位。

- **类型一致性：**
  - service 暴露 `health()`、`search(query, top_k)`、`chat(question)`。
  - API 层统一返回 `{"ok": true, "data": ...}`。
  - health 字段统一为 `available`、`database_available`、`chroma_available`、`chat_available`、`message`。
