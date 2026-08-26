"""Internal RAG APIs for SC-Wiki."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.models import Paper, PaperChunk, PaperEvidence, PaperFile, User
from backend.rag import service
from backend.security import get_current_admin, get_current_user

router = APIRouter(prefix="/api/rag", tags=["rag"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PAPER_TYPES = {"theoretical", "experimental", "review"}
THEORETICAL_SUBTYPES = {"calculation", "method", "theory"}
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class SubmitUploadOptions(BaseModel):
    consistency_acknowledged: bool = False


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
    material_states = draft.get("material_states")
    if not isinstance(paper, dict) or not isinstance(material_states, list):
        raise _upload_error(400, "invalid_draft", "草稿结构不完整")
    return paper, [item for item in material_states if isinstance(item, dict)]


def _reject_legacy_classification_contract(draft: dict[str, Any]) -> None:
    legacy_fields = {"sc_type", "sc_type_review_status", "type_code", "type_proposal_raw"}
    present = sorted(field for field in legacy_fields if field in draft)
    if present:
        raise _upload_error(
            400,
            "legacy_classification_contract",
            "草稿仍包含旧材料分类字段，请重新打开草稿完成一次性转换",
            fields=present,
        )


async def _resolve_draft_classifications(session, draft: dict[str, Any]) -> None:
    from backend.services.classification_catalog import (
        MATERIAL_DIMENSIONALITIES,
        resolve_material_family,
        resolve_structure_family,
    )

    for state_index, state in enumerate(draft.get("material_states") or []):
        if not isinstance(state, dict):
            continue
        dimensionality = str(state.get("material_dimensionality") or "unknown")
        if dimensionality not in MATERIAL_DIMENSIONALITIES:
            raise _upload_error(
                400,
                "invalid_material_dimensionality",
                f"第 {state_index + 1} 个材料状态的材料维度无效",
            )
        state["material_dimensionality"] = dimensionality

        family = state.get("material_family")
        if isinstance(family, dict) and str(family.get("name") or "").strip():
            term = None
            if family.get("id") not in (None, ""):
                try:
                    term = await session.get(models.MaterialFamily, int(family["id"]))
                except (TypeError, ValueError):
                    term = None
                if term is None:
                    raise _upload_error(404, "classification_not_found", "材料家族目录项不存在")
            else:
                term = await resolve_material_family(session, family.get("name"))
            resolved_family = (
                {"id": term.id, "name": term.name_zh, "status": "confirmed"}
                if term is not None
                else {"id": None, "name": str(family["name"]).strip(), "status": "pending"}
            )
            if isinstance(family.get("evidence"), dict):
                resolved_family["evidence"] = family["evidence"]
            state["material_family"] = resolved_family

        resolved_structures = []
        seen_ids: set[int] = set()
        for selection in state.get("structure_families") or []:
            if not isinstance(selection, dict) or not str(selection.get("name") or "").strip():
                continue
            term = None
            if selection.get("id") not in (None, ""):
                try:
                    term = await session.get(models.StructureFamily, int(selection["id"]))
                except (TypeError, ValueError):
                    term = None
                if term is None:
                    raise _upload_error(404, "classification_not_found", "结构家族目录项不存在")
            else:
                term = await resolve_structure_family(session, selection.get("name"))
            if term is not None:
                if term.id in seen_ids:
                    continue
                seen_ids.add(term.id)
                resolved = {"id": term.id, "name": term.name_zh, "status": "confirmed"}
            else:
                resolved = {"id": None, "name": str(selection["name"]).strip(), "status": "pending"}
            resolved["is_primary"] = bool(selection.get("is_primary"))
            if isinstance(selection.get("evidence"), dict):
                resolved["evidence"] = selection["evidence"]
            resolved_structures.append(resolved)
        state["structure_families"] = resolved_structures


def _derived_research_materials(material_states: list[dict[str, Any]]) -> list[str]:
    """按出现顺序汇总材料状态中的化学式，去空白、去重。"""
    seen: set[str] = set()
    derived: list[str] = []
    for state in material_states:
        material = str(state.get("material") or "").strip()
        if material and material not in seen:
            seen.add(material)
            derived.append(material)
    return derived


def _validate_draft(
    draft: dict[str, Any], *, partial: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paper, material_states = _draft_values(draft)
    if partial:
        # 草稿保存（PUT）仅做结构性检查，业务字段校验留给提交时执行，
        # 避免半成品草稿被 400 拒绝导致编辑丢失。
        return paper, material_states
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
    if (
        paper_type != "review"
        and not paper.get("research_materials")
        and not _derived_research_materials(material_states)
    ):
        raise _upload_error(400, "research_material_required", "非综述论文至少需要一个研究材料")

    if paper_type != "review" and not material_states:
        raise _upload_error(400, "material_state_required", "非综述论文至少需要一个材料状态")
    for state_index, state in enumerate(material_states):
        if not str(state.get("material") or "").strip():
            raise _upload_error(400, "state_material_required", f"第 {state_index + 1} 个材料状态缺少材料")
        family = state.get("material_family")
        if paper_type != "review" and (
            not isinstance(family, dict) or not str(family.get("name") or "").strip()
        ):
            raise _upload_error(
                400,
                "material_family_required",
                f"第 {state_index + 1} 个材料状态缺少材料家族",
            )
        if isinstance(family, dict):
            status = family.get("status")
            if status not in {"confirmed", "pending"}:
                raise _upload_error(400, "invalid_material_family", "材料家族状态无效")
            if status == "confirmed" and family.get("id") in (None, ""):
                raise _upload_error(400, "invalid_material_family", "已确认材料家族缺少目录 ID")
            if status == "pending" and family.get("id") not in (None, ""):
                raise _upload_error(400, "invalid_material_family", "待确认材料家族不能包含目录 ID")
        structures = [item for item in state.get("structure_families") or [] if isinstance(item, dict)]
        if sum(bool(item.get("is_primary")) for item in structures) > 1:
            raise _upload_error(400, "multiple_primary_structure_families", "一个材料状态只能有一个主结构家族")
        group_number = state.get("reported_space_group_number")
        if group_number not in (None, ""):
            try:
                valid_group_number = 1 <= int(group_number) <= 230
            except (TypeError, ValueError):
                valid_group_number = False
            if not valid_group_number:
                raise _upload_error(400, "invalid_space_group_number", f"第 {state_index + 1} 个材料状态的空间群号必须为 1–230")
        if state.get("pressure_min_gpa") not in (None, "") and state.get("pressure_max_gpa") not in (None, ""):
            pressure_min = _number(state.get("pressure_min_gpa"))
            pressure_max = _number(state.get("pressure_max_gpa"))
            if pressure_min is not None and pressure_max is not None and pressure_min > pressure_max:
                raise _upload_error(400, "invalid_pressure_range", f"第 {state_index + 1} 个材料状态的压强区间 min 不能大于 max")
        calculation = state.get("calculation_context")
        if isinstance(calculation, dict):
            for field, label in (("lambda_ep", "λ"), ("omega_log_k", "ωlog")):
                value = _number(calculation.get(field))
                if value is not None and value < 0:
                    raise _upload_error(400, "invalid_calculation_parameter", f"第 {state_index + 1} 个材料状态的 {label} 不能为负数")
        for tc_index, item in enumerate(state.get("tc_results") or []):
            if not isinstance(item, dict):
                continue
            kind = item.get("result_kind")
            if kind not in {"theoretical", "experimental"}:
                raise _upload_error(400, "invalid_tc_result_kind", f"第 {state_index + 1} 个材料状态的第 {tc_index + 1} 条 Tc 缺少结果类型")
            if not any(item.get(key) not in (None, "") for key in ("tc_value_k", "tc_min_k", "tc_max_k", "value_raw")):
                raise _upload_error(400, "tc_value_required", f"第 {state_index + 1} 个材料状态的第 {tc_index + 1} 条 Tc 缺少数值")
        for property_index, item in enumerate(state.get("properties") or []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("name_raw") or "").strip()
            if not name:
                raise _upload_error(400, "property_name_required", f"第 {state_index + 1} 个材料状态的第 {property_index + 1} 条普通物性缺少名称")
            if name.lower() in {"tc", "critical_temperature", "electron_phonon_coupling", "omega_log", "space_group"}:
                raise _upload_error(400, "dedicated_property_required", f"{name} 必须填写到专用字段")
            if not any(item.get(key) not in (None, "") for key in ("value", "value_min", "value_max", "value_raw")):
                raise _upload_error(400, "property_value_required", f"第 {state_index + 1} 个材料状态的第 {property_index + 1} 条普通物性缺少数值")
    for candidate_index, candidate in enumerate(draft.get("structure_candidates") or []):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("confirmation") != "confirmed" or candidate.get("status") != "confirmed":
            continue
        match = re.fullmatch(r"material_states\[(\d+)\]", str(candidate.get("material_state_ref") or ""))
        if not match or int(match.group(1)) >= len(material_states):
            raise _upload_error(
                400,
                "structure_material_state_required",
                f"第 {candidate_index + 1} 个已确认结构候选必须关联材料状态",
            )
        representations = candidate.get("representations")
        conventional = representations.get("conventional") if isinstance(representations, dict) else None
        cif = conventional.get("cif") if isinstance(conventional, dict) else None
        if not isinstance(cif, dict) or not str(cif.get("text") or "").strip():
            raise _upload_error(400, "structure_representation_missing", f"第 {candidate_index + 1} 个结构候选缺少惯用胞 CIF")
        try:
            from backend.services.structure_candidates import validate_structure_text

            candidate["validation"] = validate_structure_text("cif", str(cif["text"]))
        except Exception as exc:
            raise _upload_error(400, "structure_validation_failed", f"第 {candidate_index + 1} 个结构候选未通过服务端校验") from exc
    return paper, material_states


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


def _paper_review_context(paper_id: int) -> dict[str, Any] | None:
    from backend.database import SessionLocal

    with SessionLocal() as session:
        row = session.execute(
            select(
                Paper.id,
                Paper.upload_task_id,
                Paper.review_status,
                Paper.content_revision,
            ).where(Paper.id == paper_id)
        ).first()
    if row is None:
        return None
    return {
        "task_id": row.upload_task_id,
        "paper_id": int(row.id),
        "review_status": row.review_status,
        "paper_revision": int(row.content_revision or 1),
    }


def _artifact_by_paper_id(
    paper_id: int,
    task_id: str | None = None,
) -> tuple[str, Path, dict[str, Any]] | None:
    from backend.ingest.upload_tasks import data_path

    root = data_path("review_artifacts")
    candidates = [root / task_id / "result.json"] if task_id else root.glob("*/result.json")
    for result_path in candidates:
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if int(payload.get("paper_id") or 0) == paper_id:
            return result_path.parent.name, result_path, payload

    return None


def _validate_review_snapshot(
    context: dict[str, Any],
    task_id: str,
    payload: dict[str, Any],
) -> None:
    identity_matches = (
        int(payload.get("paper_id") or 0) == int(context["paper_id"])
        and str(payload.get("task_id") or "") == task_id
        and (not context.get("task_id") or str(context["task_id"]) == task_id)
    )
    revision_matches = int(payload.get("paper_revision") or 0) == int(
        context["paper_revision"]
    )
    if not identity_matches or not revision_matches:
        raise _upload_error(
            409,
            "review_artifact_revision_mismatch",
            "待审 AI 证据不属于论文当前版本",
        )


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


@router.get("/space-groups")
async def list_space_groups(
    current_user: User = Depends(get_current_user),
):
    from backend.services.space_groups import all_space_groups

    return {
        "space_groups": [
            {"number": item["number"], "symbol": item["symbol"]}
            for item in all_space_groups()
        ]
    }


@router.get("/upload-tasks/{task_id}/draft")
async def get_upload_draft(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import _normalize_draft
    from backend.ingest.upload_tasks import get_draft
    from backend.rag.database import async_session_factory
    from backend.services.classification_catalog import convert_legacy_draft

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
    async with async_session_factory() as session:
        result = await session.execute(select(models.MaterialFamily))
        families_by_code = {
            item.code: {"id": item.id, "name": item.name_zh}
            for item in result.scalars().all()
        }
        converted = convert_legacy_draft(draft, families_by_code=families_by_code)
        normalized = _normalize_draft(converted)
        if converted.get("classification_migration_warnings"):
            normalized["classification_migration_warnings"] = converted["classification_migration_warnings"]
        await _resolve_draft_classifications(session, normalized)
        if isinstance(draft.get("ai_original"), dict):
            ai_converted = convert_legacy_draft(
                draft["ai_original"], families_by_code=families_by_code,
            )
            normalized["ai_original"] = _normalize_draft(ai_converted)
            await _resolve_draft_classifications(session, normalized["ai_original"])
    return {"ok": True, "data": normalized}


@router.put("/upload-tasks/{task_id}/draft")
async def put_upload_draft(
    task_id: str,
    draft: dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import _normalize_draft
    from backend.ingest.upload_tasks import get_draft, save_draft
    from backend.rag.database import async_session_factory

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
    _reject_legacy_classification_contract(draft)
    previous = get_draft(task_id) or {}
    normalized = _normalize_draft(draft)
    if isinstance(previous.get("ai_original"), dict):
        normalized["ai_original"] = _normalize_draft(previous["ai_original"])
    async with async_session_factory() as session:
        await _resolve_draft_classifications(session, normalized)
    _validate_draft(normalized, partial=True)
    saved = save_draft(task_id, normalized)
    return {"ok": True, "data": saved, "saved_at": int(time.time())}


@router.post("/upload-tasks/{task_id}/structure-candidates")
async def upload_structure_candidate(
    task_id: str,
    material_state_index: int = Form(..., ge=0),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Append a CIF/POSCAR after parsing and attach it to one material state."""
    from backend.ingest.upload_jobs import _normalize_draft
    from backend.ingest.upload_contracts import structure_format_for_filename
    from backend.ingest.upload_tasks import get_draft, save_draft, task_directory, update_state
    from backend.services.structure_candidates import StructureCandidateError, build_structure_candidate

    state = _task_for_user(task_id, current_user)
    if state.get("paper_id"):
        raise _upload_error(409, "draft_already_submitted", "该草稿已经提交审核")
    if state.get("status") != "ready":
        raise _upload_error(409, "draft_not_ready", "解析完成后才能上传结构附件")

    filename = Path(file.filename or "structure.cif").name
    structure_format = structure_format_for_filename(filename)
    if structure_format is None:
        raise _upload_error(400, "unsupported_structure_type", "只支持 CIF 或 VASP 结构文件（POSCAR、CONTCAR、.poscar、.vasp）")

    raw = await file.read()
    await file.close()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise _upload_error(413, "file_too_large", "结构文件超过 50 MB 限制")
    try:
        structure_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _upload_error(400, "structure_encoding_invalid", "结构文件必须使用 UTF-8 编码") from exc

    draft = get_draft(task_id)
    if draft is None:
        raise _upload_error(409, "draft_not_ready", "草稿尚未生成")
    normalized_draft = _normalize_draft(draft)
    material_states = normalized_draft.get("material_states") or []
    if material_state_index >= len(material_states):
        raise _upload_error(400, "material_state_not_found", "指定材料状态不存在")

    file_id = uuid.uuid4().hex
    source_info = {
        "file_id": file_id,
        "filename": filename,
        "role": "attachment",
        "page": None,
        "quote": None,
    }
    try:
        candidate = build_structure_candidate(
            structure_format=structure_format,
            structure_text=structure_text,
            source=source_info,
            material_state_ref=f"material_states[{material_state_index}]",
        )
    except (StructureCandidateError, ValueError) as exc:
        raise _upload_error(400, "structure_validation_failed", str(exc)) from exc

    destination = task_directory(task_id) / f"{file_id}{Path(filename).suffix or '.POSCAR'}"
    destination.write_bytes(raw)
    files = list(state.get("files") or [])
    previous_files = list(files)
    files.append({
        "file_id": file_id,
        "role": "attachment",
        "original_filename": filename,
        "media_type": file.content_type,
        "kind": structure_format,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "sort_order": len(files),
        "upload_status": "completed",
        "extraction_status": "completed",
        "error": None,
        "stored_path": str(destination),
        "source_file_path": f"upload_PDFs/{task_id}/{destination.name}",
    })
    candidates = [item for item in normalized_draft.get("structure_candidates") or [] if isinstance(item, dict)]
    candidates.append(candidate)
    normalized_draft["structure_candidates"] = candidates
    try:
        update_state(task_id, files=files)
        save_draft(task_id, normalized_draft)
    except Exception:
        try:
            update_state(task_id, files=previous_files)
        except Exception:
            pass
        destination.unlink(missing_ok=True)
        raise
    return {"ok": True, "data": candidate}


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
    update_state(
        task_id, status="queued", retry=True,
        processing_status="processing", processing_error=None, error_code=None,
    )
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
        status="ready",
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
    from backend.ingest.scientific_drafts import (
        add_scientific_evidence_link,
        persist_scientific_draft,
    )
    from backend.ingest.upload_jobs import _normalize_draft, normalize_doi
    from backend.ingest.upload_tasks import markdown_path
    from backend.rag.database import async_session_factory

    _reject_legacy_classification_contract(draft)
    draft = _normalize_draft(draft)
    paper_data, material_states = _validate_draft(draft)
    doi = normalize_doi(paper_data.get("doi"))
    md_path = markdown_path(task_id)
    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

    try:
        async with async_session_factory() as session:
            async with session.begin():
                await _resolve_draft_classifications(session, draft)
                paper_data, material_states = _validate_draft(draft)
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

                derived_materials = _derived_research_materials(material_states)
                if derived_materials:
                    paper_data["research_materials"] = derived_materials

                paper = Paper(
                    upload_task_id=task_id,
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
                    methodology=json.dumps(paper_data.get("methodology") or [], ensure_ascii=False),
                    key_finding=paper_data.get("key_finding"),
                    rationale=draft.get("classification_reason") or paper_data.get("rationale"),
                    research_materials=paper_data.get("research_materials") or [],
                    material_relations=paper_data.get("material_relations") or [],
                    builds_on=paper_data.get("builds_on") or [],
                    review_status="pending",
                    uploaded_by_user_id=int(state["user_id"]),
                )
                session.add(paper)
                await session.flush()

                paper_files: dict[str, PaperFile] = {}
                source_files = state.get("files") or []
                if not source_files and state.get("source_file_path"):
                    source_files = [{
                        "file_id": "main",
                        "role": "main",
                        "original_filename": state.get("filename") or "paper.pdf",
                        "source_file_path": state.get("source_file_path"),
                        "sha256": state.get("file_sha256") or "",
                        "size": state.get("file_size") or 0,
                        "sort_order": 0,
                    }]
                for index, source in enumerate(source_files):
                    paper_file = PaperFile(
                        paper_id=paper.id,
                        paper_revision=paper.content_revision,
                        role=source.get("role") or "attachment",
                        original_filename=source.get("original_filename") or source.get("filename") or "file",
                        stored_path=source.get("source_file_path") or "",
                        sha256=source.get("sha256") or "",
                        size=int(source.get("size") or 0),
                        media_type=source.get("media_type"),
                        sort_order=int(source.get("sort_order", index)),
                    )
                    session.add(paper_file)
                    await session.flush()
                    paper_files[str(source.get("file_id") or index)] = paper_file

                scientific_targets = await persist_scientific_draft(session, paper, draft)

                extracted_root = md_path.parent / task_id
                if source_files and extracted_root.is_dir():
                    chunk_sources = []
                    for source in source_files:
                        file_id = str(source.get("file_id") or "")
                        source_md = extracted_root / f"{file_id}.md"
                        if source_md.exists():
                            chunk_sources.append((file_id, source_md.read_text(encoding="utf-8")))
                else:
                    chunk_sources = [("main", markdown)] if markdown else []
                paper_chunks: dict[tuple[str, int], PaperChunk] = {}
                main_paper_file = next(
                    (item for item in paper_files.values() if item.role == "main"),
                    None,
                )
                for file_id, source_markdown in chunk_sources:
                    for chunk in chunk_paper(source_markdown, paper.id):
                        page_match = re.search(r"<!--\s*page:\s*(\d+)\s*-->", chunk.content)
                        page = int(page_match.group(1)) if page_match else None
                        paper_file = paper_files.get(file_id) or main_paper_file
                        if paper_file is None:
                            continue
                        paper_chunk = PaperChunk(
                            paper_id=paper.id,
                            paper_revision=paper.content_revision,
                            paper_file_id=paper_file.id,
                            chunk_index=chunk.chunk_index,
                            section_name=chunk.section_name,
                            heading=chunk.heading,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            page_start=page,
                            page_end=page,
                        )
                        session.add(paper_chunk)
                        await session.flush()
                        paper_chunks[(str(file_id), int(chunk.chunk_index))] = paper_chunk

                evidence_groups = [
                    ("classification", draft.get("classification_evidence") or []),
                    *[(target.field_path, [target.evidence]) for target in scientific_targets],
                ]
                targets_by_path = {target.field_path: target for target in scientific_targets}
                for field_path, evidences in evidence_groups:
                    for evidence in evidences:
                        if not isinstance(evidence, dict) or not str(evidence.get("quote") or "").strip():
                            continue
                        file_id = str(evidence.get("file_id") or "")
                        chunk_index = evidence.get("chunk_index")
                        paper_chunk = None
                        if chunk_index is not None:
                            paper_chunk = paper_chunks.get((file_id, int(chunk_index)))
                            if paper_chunk is None:
                                matches = [
                                    item
                                    for (_source_file_id, source_index), item in paper_chunks.items()
                                    if source_index == int(chunk_index)
                                ]
                                if len(matches) == 1:
                                    paper_chunk = matches[0]
                        page = evidence.get("page") or evidence.get("page_start")
                        if paper_chunk is None and page is not None:
                            matches = [
                                item
                                for item in paper_chunks.values()
                                if item.page_start is not None
                                and item.page_end is not None
                                and item.page_start <= int(page) <= item.page_end
                            ]
                            if len(matches) == 1:
                                paper_chunk = matches[0]
                        if paper_chunk is None:
                            continue
                        paper_evidence = PaperEvidence(
                            paper_id=paper.id,
                            paper_revision=paper.content_revision,
                            paper_chunk_id=paper_chunk.id,
                            field_path=field_path,
                            section=evidence.get("section"),
                            page_start=page,
                            page_end=evidence.get("page_end") or page,
                            quote=str(evidence["quote"]),
                        )
                        session.add(paper_evidence)
                        await session.flush()
                        target = targets_by_path.get(field_path)
                        if target is not None:
                            add_scientific_evidence_link(session, target, paper_evidence)
                paper_id = paper.id
        return paper_id
    except IntegrityError as exc:
        raise _upload_error(409, "scientific_data_integrity_error", "科学数据不满足完整性约束") from exc


async def _submitted_paper_for_task(task_id: str) -> dict[str, Any] | None:
    from backend.rag.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                Paper.id,
                Paper.uploaded_by_user_id,
                Paper.review_status,
                Paper.content_revision,
            ).where(Paper.upload_task_id == task_id)
        )
        row = result.first()
    if row is None:
        return None
    return {
        "paper_id": int(row.id),
        "uploaded_by_user_id": (
            int(row.uploaded_by_user_id) if row.uploaded_by_user_id is not None else None
        ),
        "review_status": row.review_status,
        "paper_revision": int(row.content_revision or 1),
    }


def _record_submitted_upload(
    task_id: str,
    paper_id: int,
    draft: dict[str, Any],
    *,
    paper_revision: int = 1,
) -> None:
    from backend.ingest.upload_tasks import artifact_path, update_state

    result_path = artifact_path(task_id)
    artifact = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    snapshot = {
        "task_id": task_id,
        "paper_id": paper_id,
        "paper_revision": paper_revision,
        "ai_values": artifact.get("ai_values") or draft.get("ai_original") or {},
        "user_values": {key: value for key, value in draft.items() if key != "ai_original"},
        "evidence": artifact.get("evidence") or {},
    }
    temporary = result_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(result_path)
    update_state(
        task_id, status="submitted", paper_id=paper_id,
        review_status="pending", submission_status="submitted",
    )


def _recover_submitted_upload(task_id: str, submitted: dict[str, Any]) -> None:
    """尽力补完提交后的快照与临时清理；正式论文结果不依赖该步骤。"""
    from backend.ingest.upload_contracts import CleanupContext
    from backend.ingest.upload_tasks import cleanup_transient_data, get_draft, get_state

    try:
        state = get_state(task_id)
        draft = get_draft(task_id) if state else None
        if not state or not draft:
            return
        context = CleanupContext.from_state(task_id, state)
        _record_submitted_upload(
            task_id,
            int(submitted["paper_id"]),
            draft,
            paper_revision=int(submitted.get("paper_revision") or 1),
        )
        cleanup_transient_data(
            task_id,
            context=context,
            preserve_review_snapshot=True,
        )
    except Exception as exc:
        print(f"  [上传] task_id={task_id} 已提交，但临时数据收尾仍待重试: {exc}")


@router.post("/upload-tasks/{task_id}/submit")
async def submit_upload_draft(
    task_id: str,
    current_user: User = Depends(get_current_user),
    options: SubmitUploadOptions | None = None,
):
    try:
        from backend.ingest.upload_tasks import upload_task_lock

        with upload_task_lock(task_id):
            if options and options.consistency_acknowledged:
                return await _submit_upload_draft_locked(
                    task_id, current_user, consistency_acknowledged=True,
                )
            return await _submit_upload_draft_locked(task_id, current_user)
    except TimeoutError as exc:
        raise _upload_error(409, "submission_in_progress", "该上传任务正在提交，请稍后重试") from exc


async def _submit_upload_draft_locked(
    task_id: str,
    current_user: User,
    *,
    consistency_acknowledged: bool = False,
) -> dict[str, Any]:
    from backend.ingest.upload_contracts import CleanupContext
    from backend.ingest.upload_tasks import cleanup_transient_data, get_draft, update_state

    submitted = await _submitted_paper_for_task(task_id)
    if submitted is not None:
        if int(submitted.get("uploaded_by_user_id") or 0) != current_user.id:
            raise _upload_error(403, "submit_forbidden", "只有上传者可以提交草稿")
        _recover_submitted_upload(task_id, submitted)
        return {
            "ok": True,
            "paper_id": int(submitted["paper_id"]),
            "review_status": submitted.get("review_status") or "pending",
        }

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
    if (state.get("consistency") or {}).get("status") == "warning" and not consistency_acknowledged:
        raise _upload_error(
            409, "consistency_ack_required",
            "正文与附件的标题、DOI 或作者存在明确差异，请确认这些文件属于同一篇论文",
        )
    if state.get("stage") != "ready" or state.get("processing_status") != "succeeded":
        raise _upload_error(409, "draft_not_ready", "草稿尚未准备完成")
    draft = get_draft(task_id)
    if draft is None:
        raise _upload_error(409, "draft_not_found", "草稿不存在或已过期")

    cleanup_context = CleanupContext.from_state(task_id, state)
    update_state(task_id, status="submitting", submission_status="submitting")
    try:
        paper_id = await _create_pending_paper(task_id, state, draft)
    except Exception:
        # 提交失败必须回滚为 ready，否则任务卡在 submitting、详情页只剩空白只读预览
        try:
            update_state(task_id, status="ready", submission_status="failed")
        except Exception:
            pass
        raise
    try:
        _record_submitted_upload(task_id, paper_id, draft, paper_revision=1)
    except Exception as exc:
        print(f"  [上传] paper_id={paper_id} 已提交，但临时审核证据更新失败: {exc}")
    else:
        try:
            cleanup_transient_data(
                task_id,
                context=cleanup_context,
                preserve_review_snapshot=True,
            )
        except Exception as exc:
            print(f"  [上传] paper_id={paper_id} 已提交，但临时数据清理失败: {exc}")
    return {"ok": True, "paper_id": paper_id, "review_status": "pending"}


@router.get("/papers/{paper_id}/review-artifact")
async def get_paper_review_artifact(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    context = _paper_review_context(paper_id)
    if context is None:
        raise _upload_error(404, "paper_not_found", "论文不存在")
    if context["review_status"] != "pending":
        raise _upload_error(409, "review_artifact_not_pending", "论文已不在待审核状态")
    found = _artifact_by_paper_id(paper_id, context.get("task_id"))
    if not found:
        raise _upload_error(404, "review_artifact_not_found", "该论文没有待审 AI 证据")
    task_id, _path, payload = found
    _validate_review_snapshot(context, task_id, payload)
    return {
        "ok": True,
        "data": {
            "task_id": task_id,
            "paper_id": paper_id,
            "paper_revision": context["paper_revision"],
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
    context = _paper_review_context(paper_id)
    if context is None:
        raise _upload_error(404, "paper_not_found", "论文不存在")
    if context["review_status"] == "pending":
        raise _upload_error(409, "review_artifact_still_pending", "论文仍在待审核状态")
    if context["review_status"] not in {"approved", "rejected"}:
        raise _upload_error(409, "review_artifact_not_terminal", "论文审核状态不允许清理")
    found = _artifact_by_paper_id(paper_id, context.get("task_id"))
    if not found:
        return {"ok": True, "paper_id": paper_id, "cleaned": False}
    task_id, result_path, payload = found
    _validate_review_snapshot(context, task_id, payload)
    shutil.rmtree(result_path.parent, ignore_errors=True)
    return {"ok": True, "paper_id": paper_id, "cleaned": True}
