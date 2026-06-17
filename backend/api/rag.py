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
