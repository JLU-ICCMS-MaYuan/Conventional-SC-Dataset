"""Internal RAG APIs for SC-Wiki."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Literal

import anyio
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.rag import service


router = APIRouter(prefix="/api/rag", tags=["rag"])


class RagMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RagChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(15, ge=1, le=50)
    rerank_top_k: int = Field(5, ge=1, le=20)
    history: list[RagMessage] = Field(default_factory=list)
    explore: bool = Field(False, description="是否启用灵感探索模式")


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
    if isinstance(exc, service.RagNotFoundError):
        return _service_error(404, str(exc) or "资源不存在")
    if isinstance(exc, service.RagInternalError):
        return _service_error(502, "AI 文献助手返回错误", str(exc))
    return _service_error(502, "AI 文献助手返回错误", str(exc))


def _history_dicts(messages: list[RagMessage]) -> list[dict[str, str]]:
    return [{"role": item.role, "content": item.content} for item in messages if item.content.strip()]


async def _call_service(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except TypeError as exc:
        unexpected_mode = "unexpected keyword argument 'mode'" in str(exc)
        unexpected_chat_args = (
            "unexpected keyword argument 'top_k'" in str(exc)
            or "unexpected keyword argument 'rerank_top_k'" in str(exc)
            or "unexpected keyword argument 'history'" in str(exc)
        )
        if "mode" in kwargs and unexpected_mode:
            kwargs.pop("mode")
            return await func(*args, **kwargs)
        if unexpected_chat_args:
            return await func(*args)
        raise


def _sse(event_type: str, data: Any) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
async def rag_health():
    return service.health()


@router.get("/stats")
async def rag_stats():
    try:
        data = await service.stats()
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.get("/search/detect")
async def rag_detect_search_mode(q: str = Query(...)):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    try:
        data = service.detect_search_mode(query)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.get("/search")
async def rag_search(
    q: str = Query(...),
    mode: str | None = Query(None),
    top_k: int = Query(10, ge=1, le=50),
):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    try:
        data = await _call_service(service.search, query, mode=mode, top_k=top_k)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.post("/chat")
async def rag_chat(request: RagChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    try:
        data = await _call_service(
            service.chat,
            question,
            top_k=request.top_k,
            rerank_top_k=request.rerank_top_k,
            history=_history_dicts(request.history),
        )
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.post("/chat/stream")
async def rag_chat_stream(request: RagChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    async def event_generator():
        try:
            async for event in service.chat_stream(
                question,
                top_k=request.top_k,
                rerank_top_k=request.rerank_top_k,
                history=_history_dicts(request.history),
                explore=request.explore,
            ):
                yield _sse(event.get("type", "message"), event.get("data"))
            yield _sse("end", {"ok": True})
        except Exception as exc:
            mapped = _map_internal_error(exc)
            yield _sse("error", mapped.detail)
            yield _sse("end", {"ok": False})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/papers")
async def rag_papers(
    keyword: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        data = await service.list_papers(keyword=keyword.strip() if keyword else None, limit=limit)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.get("/papers/{paper_id}")
async def rag_paper_detail(paper_id: int):
    try:
        data = await service.paper_detail(paper_id)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.get("/superconductors")
async def rag_superconductors(
    formula: str | None = Query(None),
    elements: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        data = await service.search_superconductors(
            formula=formula.strip() if formula else None,
            elements=elements.strip() if elements else None,
            limit=limit,
        )
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.get("/superconductors/{superconductor_id}")
async def rag_superconductor_detail(superconductor_id: int):
    try:
        data = await service.superconductor_detail(superconductor_id)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    return {"ok": True, "data": data}


@router.post("/upload-pdf")
async def rag_upload_pdf(file: UploadFile = File(...)):
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    suffix = Path(filename).suffix or ".pdf"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = Path(tmp.name)
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)
        data = await service.upload_pdf(temp_path, filename)
    except Exception as exc:
        raise _map_internal_error(exc) from exc
    finally:
        if temp_path is not None:
            await anyio.Path(temp_path).unlink(missing_ok=True)
        await file.close()

    return {"ok": True, "data": data}


@router.post("/upload-text")
async def rag_upload_text(file: UploadFile = File(...)):
    """上传 TXT/MD 文本文件，从 extractor 开始走摄入管线"""
    filename = file.filename or "uploaded.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".txt", ".md"):
        raise HTTPException(status_code=400, detail="只支持 TXT/MD 文件")

    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        try:
            await file.seek(0)
            content = (await file.read()).decode("gbk")
        except Exception:
            raise HTTPException(status_code=400, detail="无法解码文件内容，请使用 UTF-8 编码")
    finally:
        await file.close()

    from backend.ingest.extractor import extract_from_markdown
    from backend.ingest.store_papers import store_extraction
    from backend.rag.database import async_session_factory

    result = extract_from_markdown(content)
    async with async_session_factory() as session:
        paper_id = await store_extraction(result, filename, session)
        return {"ok": True, "paper_id": paper_id, "title": result.paper.get("title", "")}
