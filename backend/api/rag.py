"""Internal RAG APIs for SC-Wiki."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import KeyProperty, Paper, PaperChunk, User
from backend.rag import service
from backend.security import get_current_admin, get_current_user

router = APIRouter(prefix="/api/rag", tags=["rag"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PAPER_TYPES = {"theoretical", "experimental", "review"}
THEORETICAL_SUBTYPES = {"calculation", "method", "theory"}
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


def _upload_error(status_code: int, code: str, message: str, **extra: Any) -> HTTPException:
    detail = {"code": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def _is_admin(user: User) -> bool:
    return user.role in {"admin", "superadmin"} and user.is_approved


def _task_for_user(task_id: str, user: User) -> dict[str, Any]:
    from backend.ingest.upload_tasks import get_state

    state = get_state(task_id)
    if not state:
        raise _upload_error(404, "upload_task_not_found", "上传任务不存在或已过期")
    if int(state.get("user_id") or 0) != user.id and not _is_admin(user):
        raise _upload_error(403, "upload_task_forbidden", "无权访问该上传任务")
    return state


async def _save_task_upload(file: UploadFile, user: User, file_kind: str) -> dict[str, Any]:
    from backend.ingest.upload_jobs import sha256_file
    from backend.ingest.upload_tasks import (
        cleanup_task_files,
        create_task,
        enqueue_processing,
        schedule_cleanup,
        task_directory,
        update_state,
    )

    filename = Path(file.filename or f"uploaded.{file_kind}").name
    state = create_task(user.id, filename, file_kind)
    task_id = state["task_id"]
    destination = task_directory(task_id) / filename
    total = 0
    try:
        with destination.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise _upload_error(413, "file_too_large", "文件超过 50 MB 限制")
                stream.write(chunk)
    except Exception:
        cleanup_task_files(task_id)
        raise
    finally:
        await file.close()

    relative_path = f"upload_PDFs/{task_id}/{filename}"
    update_state(
        task_id,
        file_path=str(destination),
        source_file_path=relative_path,
        file_size=total,
        file_sha256=sha256_file(destination),
    )
    try:
        enqueue_processing(task_id)
        schedule_cleanup(task_id)
    except Exception as exc:
        update_state(
            task_id,
            processing_status="failed",
            processing_error=f"任务队列不可用：{exc}",
            error_code="upload_queue_unavailable",
        )
        try:
            schedule_cleanup(task_id)
        except Exception as cleanup_exc:
            print(f"  [上传] task_id={task_id} 无法安排过期清理: {cleanup_exc}")
        raise _upload_error(
            503,
            "upload_queue_unavailable",
            "文件已保存，但解析任务暂时无法启动",
            task_id=task_id,
        ) from exc
    return _task_for_user(task_id, user)


def _draft_values(draft: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paper = draft.get("paper")
    properties = draft.get("key_properties")
    if not isinstance(paper, dict) or not isinstance(properties, list):
        raise _upload_error(400, "invalid_draft", "草稿结构不完整")
    return paper, [item for item in properties if isinstance(item, dict)]


def _validate_draft(draft: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paper, properties = _draft_values(draft)
    if not str(paper.get("title") or "").strip():
        raise _upload_error(400, "title_required", "论文标题不能为空")

    doi = str(paper.get("doi") or "").strip()
    if doi and not DOI_PATTERN.match(doi):
        raise _upload_error(400, "invalid_doi", "DOI 格式不正确")

    paper_type = str(paper.get("paper_type") or "")
    if paper_type not in PAPER_TYPES:
        raise _upload_error(400, "paper_type_required", "请选择论文整体类型")
    subtype = paper.get("theoretical_subtype")
    if paper_type == "theoretical" and subtype not in THEORETICAL_SUBTYPES:
        raise _upload_error(400, "theoretical_subtype_required", "理论论文必须选择二级类型")
    if paper_type != "theoretical":
        paper["theoretical_subtype"] = None
    if paper_type != "review" and not paper.get("research_materials"):
        raise _upload_error(400, "research_material_required", "非综述论文至少需要一个研究材料")

    suggested_sc_type = str(draft.get("sc_type") or "")
    if len(suggested_sc_type) > 20:
        raise _upload_error(400, "sc_type_too_long", "超导材料类型最多 20 个字符")
    for index, item in enumerate(properties):
        if not str(item.get("material") or "").strip():
            raise _upload_error(400, "property_material_required", f"第 {index + 1} 条物性缺少材料")
        if not str(item.get("name") or item.get("name_raw") or "").strip():
            raise _upload_error(400, "property_name_required", f"第 {index + 1} 条物性缺少名称")
        has_value = any(item.get(key) not in (None, "") for key in ("value", "value_min", "value_max", "value_raw"))
        if not has_value:
            raise _upload_error(400, "property_value_required", f"第 {index + 1} 条物性缺少数值或原始文本")
        if item.get("article_type") not in {"e", "t"}:
            raise _upload_error(400, "property_article_type_required", f"第 {index + 1} 条物性必须标记实验值或理论值")
        sc_type = str(item.get("superconductor_type") or suggested_sc_type)
        if len(sc_type) > 20:
            raise _upload_error(400, "sc_type_too_long", f"第 {index + 1} 条物性的材料类型最多 20 个字符")
    return paper, properties


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
        return float(match.group()) if match else None


def _property_values(item: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
    from backend.scripts.rebuild_from_clean_results import parse_range

    if item.get("value_min") is not None or item.get("value_max") is not None:
        return _number(item.get("value_min")), _number(item.get("value_max")), item.get("value_raw")
    return parse_range(item.get("value_raw") or item.get("value"))


def _artifact_by_paper_id(paper_id: int) -> tuple[str, Path, dict[str, Any]] | None:
    from backend.database import SessionLocal
    from backend.ingest.upload_tasks import data_path

    root = data_path("review_artifacts")
    try:
        with SessionLocal() as session:
            source_file_path = session.scalar(
                select(Paper.source_file_path).where(Paper.id == paper_id)
            )
        match = re.match(r"^upload_PDFs/([0-9a-f]{32})/", source_file_path or "")
        if match:
            result_path = root / match.group(1) / "result.json"
            if result_path.is_file():
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                payload["paper_id"] = paper_id
                return match.group(1), result_path, payload
    except (OSError, json.JSONDecodeError, SQLAlchemyError):
        pass

    # 兼容 source_file_path 缺失或旧版审核证据。
    for result_path in root.glob("*/result.json"):
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if int(payload.get("paper_id") or 0) == paper_id:
            return result_path.parent.name, result_path, payload
    return None


def _candidate_attachments(paper_id: int) -> list[dict[str, Any]]:
    from backend.ingest.upload_tasks import data_path

    root = data_path("upload_PDFs") / "candidates" / str(paper_id)
    if not root.is_dir():
        return []
    attachments: list[dict[str, Any]] = []
    for metadata_path in sorted(root.glob("*.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        task_id = str(metadata.get("task_id") or metadata_path.stem)
        file_path = next(
            (path for path in root.glob(f"{task_id}.*") if path.suffix.lower() != ".json"),
            None,
        )
        if not file_path or not file_path.is_file():
            continue
        attachments.append({
            "id": task_id,
            "filename": metadata.get("filename") or file_path.name,
            "file_sha256": metadata.get("file_sha256"),
            "file_size": file_path.stat().st_size,
            "uploaded_by_user_id": metadata.get("user_id"),
            "created_at": metadata.get("created_at"),
        })
    return attachments


def _candidate_attachment_path(paper_id: int, attachment_id: str) -> tuple[Path, str] | None:
    if not re.fullmatch(r"[0-9a-f]{32}", attachment_id):
        return None
    from backend.ingest.upload_tasks import data_path

    root = data_path("upload_PDFs") / "candidates" / str(paper_id)
    metadata_path = root / f"{attachment_id}.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    file_path = next(
        (path for path in root.glob(f"{attachment_id}.*") if path.suffix.lower() != ".json"),
        None,
    )
    if not file_path or not file_path.is_file():
        return None
    return file_path, Path(str(metadata.get("filename") or file_path.name)).name


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
async def rag_upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise _upload_error(400, "unsupported_file_type", "只支持 PDF 文件")
    state = await _save_task_upload(file, current_user, "pdf")
    return JSONResponse(
        status_code=202,
        content={
            "ok": True,
            "task_id": state["task_id"],
            "filename": state["filename"],
            "stage": state["stage"],
            "stage_index": state["stage_index"],
            "stage_total": state["stage_total"],
            "processing_status": state["processing_status"],
        },
    )


@router.post("/upload-text")
async def rag_upload_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or "uploaded.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".txt", ".md"):
        raise _upload_error(400, "unsupported_file_type", "只支持 TXT/MD 文件")
    state = await _save_task_upload(file, current_user, suffix.lstrip("."))
    return JSONResponse(
        status_code=202,
        content={
            "ok": True,
            "task_id": state["task_id"],
            "filename": state["filename"],
            "stage": state["stage"],
            "stage_index": state["stage_index"],
            "stage_total": state["stage_total"],
            "processing_status": state["processing_status"],
        },
    )


@router.get("/upload-tasks/{task_id}")
async def get_upload_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    return {"ok": True, "data": _task_for_user(task_id, current_user)}


@router.get("/upload-tasks/{task_id}/draft")
async def get_upload_draft(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import _normalize_draft
    from backend.ingest.upload_tasks import get_draft

    state = _task_for_user(task_id, current_user)
    if state.get("duplicate"):
        raise _upload_error(
            409,
            "duplicate_doi",
            "该论文已经存在",
            existing_paper_id=state.get("existing_paper_id"),
        )
    draft = get_draft(task_id)
    if draft is None:
        if state.get("processing_status") == "failed":
            raise _upload_error(409, "draft_not_ready", "解析失败，可重新解析或手动填写")
        raise _upload_error(409, "draft_not_ready", "AI 草稿尚未生成")
    normalized = _normalize_draft(draft)
    if isinstance(draft.get("ai_original"), dict):
        normalized["ai_original"] = _normalize_draft(draft["ai_original"])
    return {"ok": True, "data": normalized}


@router.put("/upload-tasks/{task_id}/draft")
async def put_upload_draft(
    task_id: str,
    draft: dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import _normalize_draft
    from backend.ingest.upload_tasks import get_draft, save_draft

    state = _task_for_user(task_id, current_user)
    if state.get("paper_id"):
        raise _upload_error(409, "draft_already_submitted", "该草稿已经提交审核")
    if state.get("duplicate"):
        raise _upload_error(
            409,
            "duplicate_doi",
            "该论文已经存在",
            existing_paper_id=state.get("existing_paper_id"),
        )
    previous = get_draft(task_id) or {}
    normalized = _normalize_draft(draft)
    if isinstance(previous.get("ai_original"), dict):
        normalized["ai_original"] = _normalize_draft(previous["ai_original"])
    _draft_values(normalized)
    saved = save_draft(task_id, normalized)
    return {"ok": True, "data": saved, "saved_at": int(time.time())}


@router.post("/upload-tasks/{task_id}/retry")
async def retry_upload_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_tasks import enqueue_processing, update_state

    state = _task_for_user(task_id, current_user)
    if state.get("paper_id"):
        raise _upload_error(409, "draft_already_submitted", "该草稿已经提交审核")
    if state.get("duplicate"):
        raise _upload_error(
            409,
            "duplicate_doi",
            "该论文已经存在",
            existing_paper_id=state.get("existing_paper_id"),
        )
    if state.get("processing_status") != "failed":
        raise _upload_error(409, "retry_not_allowed", "只有失败的任务可以重新解析")
    update_state(task_id, processing_status="processing", processing_error=None, error_code=None)
    enqueue_processing(task_id)
    return JSONResponse(
        status_code=202,
        content={"ok": True, "task_id": task_id, "status": "processing"},
    )


@router.post("/upload-tasks/{task_id}/manual")
async def use_manual_upload_draft(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import empty_draft
    from backend.ingest.upload_tasks import artifact_path, save_draft, update_state

    state = _task_for_user(task_id, current_user)
    if state.get("processing_status") != "failed":
        raise _upload_error(409, "manual_not_allowed", "只有解析失败的任务可以改为手动填写")
    draft = empty_draft()
    draft["ai_original"] = empty_draft()
    save_draft(task_id, draft)
    artifact_path(task_id).write_text(
        json.dumps(
            {
                "task_id": task_id,
                "paper_id": None,
                "ai_values": draft["ai_original"],
                "user_values": None,
                "evidence": {"classification": [], "key_properties": []},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    update_state(
        task_id,
        stage="ready",
        stage_index=5,
        processing_status="succeeded",
        processing_error=None,
        error_code=None,
        manual_mode=True,
    )
    return {"ok": True, "data": draft}


async def _create_pending_paper(
    task_id: str,
    state: dict[str, Any],
    draft: dict[str, Any],
) -> int:
    from backend.ingest.chunker import chunk_paper
    from backend.ingest.prop_names import normalize_prop_name
    from backend.ingest.upload_jobs import normalize_doi
    from backend.ingest.upload_tasks import markdown_path
    from backend.rag.database import async_session_factory

    paper_data, properties = _validate_draft(draft)
    doi = normalize_doi(paper_data.get("doi"))
    md_path = markdown_path(task_id)
    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

    try:
        async with async_session_factory() as session:
            async with session.begin():
                if doi:
                    result = await session.execute(
                        select(Paper).where(func.lower(Paper.doi).contains(doi.lower()))
                    )
                    existing = next(
                        (
                            candidate
                            for candidate in result.scalars()
                            if (normalize_doi(candidate.doi) or "").lower() == doi.lower()
                        ),
                        None,
                    )
                    if existing:
                        raise _upload_error(
                            409,
                            "duplicate_doi",
                            "该论文已经存在",
                            existing_paper_id=existing.id,
                        )

                paper = Paper(
                    doi=doi,
                    title=str(paper_data.get("title")).strip(),
                    authors=paper_data.get("authors") or None,
                    journal=paper_data.get("journal"),
                    volume=paper_data.get("volume"),
                    pages=paper_data.get("pages"),
                    year=paper_data.get("year"),
                    abstract=paper_data.get("abstract"),
                    summary=paper_data.get("summary"),
                    paper_type=paper_data.get("paper_type"),
                    theoretical_subtype=paper_data.get("theoretical_subtype"),
                    keywords_tags=json.dumps(paper_data.get("keywords_tags") or [], ensure_ascii=False),
                    source_file_path=state.get("source_file_path"),
                    methodology=json.dumps(paper_data.get("methodology") or [], ensure_ascii=False),
                    key_finding=paper_data.get("key_finding"),
                    rationale=draft.get("classification_reason") or paper_data.get("rationale"),
                    research_materials=paper_data.get("research_materials") or [],
                    referenced_materials=paper_data.get("referenced_materials") or [],
                    material_relations=paper_data.get("material_relations") or [],
                    builds_on=paper_data.get("builds_on") or [],
                    review_status="pending",
                    uploaded_by_user_id=int(state["user_id"]),
                )
                session.add(paper)
                await session.flush()

                for item in properties:
                    name_raw = str(item.get("name_raw") or item.get("name") or "").strip()
                    name, _matched = normalize_prop_name(str(item.get("name") or name_raw))
                    value_min, value_max, value_raw = _property_values(item)
                    condition = item.get("condition") if isinstance(item.get("condition"), dict) else {}
                    session.add(
                        KeyProperty(
                            paper_id=paper.id,
                            material=str(item.get("material")).strip(),
                            name=name[:100],
                            name_raw=name_raw[:255],
                            name_note=item.get("name_note"),
                            value_min=value_min,
                            value_max=value_max,
                            value_raw=value_raw,
                            unit=item.get("unit"),
                            pressure_gpa=_number(item.get("pressure_gpa") or condition.get("pressure")),
                            temperature_k=_number(item.get("temperature_k") or condition.get("temperature")),
                            condition_json=condition or None,
                            condition_note=item.get("condition_note"),
                            is_primary=bool(item.get("is_primary")),
                            superconductor_type=item.get("superconductor_type") or draft.get("sc_type") or None,
                            article_type=item.get("article_type"),
                            source_label="upload",
                            structure_text=item.get("structure_text"),
                            structure_format=item.get("structure_format"),
                        )
                    )

                for chunk in chunk_paper(markdown, paper.id) if markdown else []:
                    session.add(
                        PaperChunk(
                            paper_id=paper.id,
                            chunk_index=chunk.chunk_index,
                            section_name=chunk.section_name,
                            heading=chunk.heading,
                            content=chunk.content,
                            token_count=chunk.token_count,
                        )
                    )
                paper_id = paper.id
        return paper_id
    except IntegrityError as exc:
        raise _upload_error(409, "duplicate_doi", "该论文已经存在") from exc


async def _paper_id_for_source_path(source_file_path: str | None) -> int | None:
    if not source_file_path:
        return None
    from backend.rag.database import async_session_factory

    async with async_session_factory() as session:
        return await session.scalar(
            select(Paper.id).where(Paper.source_file_path == source_file_path)
        )


def _record_submitted_upload(task_id: str, paper_id: int, draft: dict[str, Any]) -> None:
    from backend.ingest.upload_tasks import artifact_path, update_state

    result_path = artifact_path(task_id)
    artifact = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    artifact.update(
        {
            "task_id": task_id,
            "paper_id": paper_id,
            "ai_values": artifact.get("ai_values") or draft.get("ai_original") or {},
            "user_values": {key: value for key, value in draft.items() if key != "ai_original"},
        }
    )
    result_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    update_state(
        task_id, paper_id=paper_id, review_status="pending", submission_status="submitted",
    )


@router.post("/upload-tasks/{task_id}/submit")
async def submit_upload_draft(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        from backend.ingest.upload_tasks import upload_task_lock

        with upload_task_lock(task_id):
            return await _submit_upload_draft_locked(task_id, current_user)
    except TimeoutError as exc:
        raise _upload_error(409, "submission_in_progress", "该上传任务正在提交，请稍后重试") from exc


async def _submit_upload_draft_locked(task_id: str, current_user: User) -> dict[str, Any]:
    from backend.ingest.upload_tasks import artifact_path, get_draft, update_state

    state = _task_for_user(task_id, current_user)
    if int(state.get("user_id") or 0) != current_user.id:
        raise _upload_error(403, "submit_forbidden", "只有上传者可以提交草稿")
    if state.get("paper_id"):
        return {"ok": True, "paper_id": state["paper_id"], "review_status": "pending"}
    if state.get("duplicate"):
        raise _upload_error(
            409, "duplicate_doi", "该论文已经存在",
            existing_paper_id=state.get("existing_paper_id"),
        )
    if state.get("stage") != "ready" or state.get("processing_status") != "succeeded":
        raise _upload_error(409, "draft_not_ready", "草稿尚未准备完成")
    draft = get_draft(task_id)
    if draft is None:
        raise _upload_error(409, "draft_not_found", "草稿不存在或已过期")

    paper_id = await _paper_id_for_source_path(state.get("source_file_path"))
    if paper_id is None:
        existing_artifact = artifact_path(task_id)
        if existing_artifact.exists():
            try:
                existing_payload = json.loads(existing_artifact.read_text(encoding="utf-8"))
                paper_id = existing_payload.get("paper_id")
            except (OSError, json.JSONDecodeError):
                pass
    if paper_id is not None:
        try:
            _record_submitted_upload(task_id, int(paper_id), draft)
        except Exception as exc:
            print(f"  [上传] paper_id={paper_id} 已存在，但临时审核证据恢复失败: {exc}")
        return {"ok": True, "paper_id": int(paper_id), "review_status": "pending"}

    update_state(task_id, submission_status="submitting")
    try:
        paper_id = await _create_pending_paper(task_id, state, draft)
    except Exception:
        try:
            update_state(task_id, submission_status="failed")
        except Exception:
            pass
        raise
    try:
        _record_submitted_upload(task_id, paper_id, draft)
    except Exception as exc:
        print(f"  [上传] paper_id={paper_id} 已提交，但临时审核证据更新失败: {exc}")
    return {"ok": True, "paper_id": paper_id, "review_status": "pending"}


@router.get("/papers/{paper_id}/review-artifact")
async def get_paper_review_artifact(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    found = _artifact_by_paper_id(paper_id)
    if not found:
        raise _upload_error(404, "review_artifact_not_found", "该论文没有待审 AI 证据")
    task_id, _path, payload = found
    return {
        "ok": True,
        "data": {
            "task_id": task_id,
            "paper_id": paper_id,
            "ai_values": payload.get("ai_values") or {},
            "user_values": payload.get("user_values") or {},
            "evidence": payload.get("evidence") or {},
        },
    }


@router.get("/papers/{paper_id}/candidate-attachments")
async def list_candidate_attachments(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    return {"ok": True, "data": _candidate_attachments(paper_id)}


@router.get("/papers/{paper_id}/candidate-attachments/{attachment_id}")
async def download_candidate_attachment(
    paper_id: int,
    attachment_id: str,
    _current_user: User = Depends(get_current_admin),
):
    found = _candidate_attachment_path(paper_id, attachment_id)
    if not found:
        raise _upload_error(404, "candidate_attachment_not_found", "候选附件不存在")
    file_path, filename = found
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")


@router.post("/papers/{paper_id}/publish")
async def publish_approved_paper(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    from backend.ingest.embedder import embed_and_index_chunks
    from backend.rag.database import async_session_factory

    async with async_session_factory() as session:
        paper = await session.scalar(
            select(Paper).where(Paper.id == paper_id, Paper.review_status == "approved")
        )
        if paper is None:
            raise _upload_error(409, "paper_not_approved", "论文尚未审核通过，不能发布向量索引")
        result = await session.execute(
            select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.chunk_index)
        )
        chunks = list(result.scalars())

    chunk_data = [
        {
            "id": str(chunk.id),
            "paper_id": paper_id,
            "chunk_index": chunk.chunk_index,
            "section_name": chunk.section_name or "",
            "content": chunk.content,
        }
        for chunk in chunks
    ]
    indexed = await asyncio.to_thread(embed_and_index_chunks, chunk_data)
    return {"ok": True, "paper_id": paper_id, "indexed_chunks": indexed}


@router.delete("/papers/{paper_id}/review-artifact")
async def delete_paper_review_artifact(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    from backend.ingest.upload_tasks import draft_key, redis_client, task_key

    found = _artifact_by_paper_id(paper_id)
    if not found:
        raise _upload_error(404, "review_artifact_not_found", "该论文没有待审 AI 证据")
    task_id, result_path, _payload = found
    shutil.rmtree(result_path.parent, ignore_errors=True)
    redis_client().delete(task_key(task_id), draft_key(task_id))
    return {"ok": True, "paper_id": paper_id, "cleaned": True}
