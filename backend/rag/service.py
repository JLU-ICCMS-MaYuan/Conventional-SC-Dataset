"""Stable service facade for SC-Wiki internal RAG APIs."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from pathlib import Path
from typing import Any, AsyncIterator

from sqlalchemy import desc, func, select
from sqlalchemy.orm import joinedload

from backend.rag.config import get_rag_settings


class RagDataUnavailableError(RuntimeError):
    """Raised when the RAG database or Chroma data is unavailable."""


class RagChatUnavailableError(RuntimeError):
    """Raised when LLM-backed chat is not configured."""


class RagInternalError(RuntimeError):
    """Raised when the internal RAG runtime fails unexpectedly."""


class RagNotFoundError(RuntimeError):
    """Raised when a requested RAG resource does not exist."""


def _loads_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def health() -> dict[str, Any]:
    settings = get_rag_settings()
    database_available = settings.database_available
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


def _ensure_chat_available() -> None:
    _ensure_data_available()
    if not get_rag_settings().chat_configured:
        raise RagChatUnavailableError("LLM 问答未配置")


async def search(query: str, top_k: int = 10, mode: str | None = None) -> dict[str, Any]:
    _ensure_data_available()
    try:
        from backend.rag.search.engine import search as rag_search

        return await rag_search(query, mode=mode, top_k=top_k)
    except (RagDataUnavailableError, RagChatUnavailableError):
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


def detect_search_mode(query: str) -> dict[str, str]:
    try:
        from backend.rag.search.engine import SEARCH_MODES, detect_search_mode as detect

        mode = detect(query)
        return {"query": query, "mode": mode, "description": SEARCH_MODES.get(mode, "")}
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def chat(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    _ensure_chat_available()
    try:
        from backend.rag.agent import run

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        prev_msgs = None
        if history:
            prev_msgs = []
            for h in history[-20:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role == "assistant":
                    prev_msgs.append(AIMessage(content=content))
                elif role == "system":
                    prev_msgs.append(SystemMessage(content=content))
                else:
                    prev_msgs.append(HumanMessage(content=content))

        return run(question, prev_messages=prev_msgs)
    except (RagDataUnavailableError, RagChatUnavailableError):
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def chat_stream(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    history: list[dict[str, str]] | None = None,
    explore: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    _ensure_chat_available()

    if explore:
        # 探索模式 — Inspiration Agent (多轮，在线程池中运行)
        try:
            from backend.rag.agent import run
            from langchain_core.messages import HumanMessage, AIMessage

            prev_msgs = None
            if history:
                prev_msgs = []
                for h in history[-20:]:
                    role = h.get("role", "user")
                    content = h.get("content", "")
                    if role == "assistant":
                        prev_msgs.append(AIMessage(content=content))
                    else:
                        prev_msgs.append(HumanMessage(content=content))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = await asyncio.get_event_loop().run_in_executor(
                    pool, run, question, prev_msgs
                )

            answer = result.get("answer", "")
            # 流式输出
            for char in answer:
                yield {"type": "token", "data": char}

            yield {
                "type": "done",
                "data": {
                    "answer": answer,
                    "source": f"inspire_{result.get('mode', '')}",
                    "ideas": result.get("ideas", []),
                },
            }
            return
        except (RagDataUnavailableError, RagChatUnavailableError):
            raise
        except Exception as exc:
            raise RagInternalError(str(exc)) from exc

    # 普通问答 — Mentor Agent
    try:
        from backend.rag.agent.mentor import run_stream

        # history → LangChain 消息格式
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        prev_msgs = None
        if history:
            prev_msgs = []
            for h in history[-20:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role == "assistant":
                    prev_msgs.append(AIMessage(content=content))
                elif role == "system":
                    prev_msgs.append(SystemMessage(content=content))
                else:
                    prev_msgs.append(HumanMessage(content=content))

        async for event in run_stream(question, prev_messages=prev_msgs):
            yield event
    except (RagDataUnavailableError, RagChatUnavailableError):
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def stats() -> dict[str, Any]:
    _ensure_data_available()
    try:
        from backend.rag.database import async_session_factory
        from backend.rag.models import ChemicalSystem, KeyProperty, Paper, PaperChunk, Superconductor
        from backend.rag.vectordb import collection_stats

        async with async_session_factory() as session:
            paper_count = (await session.execute(select(func.count()).select_from(Paper))).scalar() or 0
            sc_count = (await session.execute(select(func.count()).select_from(Superconductor))).scalar() or 0
            record_count = (await session.execute(select(func.count()).select_from(KeyProperty))).scalar() or 0
            chunk_count = (await session.execute(select(func.count()).select_from(PaperChunk))).scalar() or 0
            sys_count = (await session.execute(select(func.count()).select_from(ChemicalSystem))).scalar() or 0
            paper_type_rows = (await session.execute(
                select(Paper.paper_type, func.count()).group_by(Paper.paper_type)
            )).all()

        try:
            chroma_chunks = collection_stats().get("count", 0)
        except Exception:
            chroma_chunks = 0

        return {
            "papers": paper_count,
            "superconductors": sc_count,
            "records": record_count,
            "chunks": chunk_count,
            "chroma_chunks": chroma_chunks,
            "chemical_systems": sys_count,
            "paper_types": {row[0] or "unknown": row[1] for row in paper_type_rows},
        }
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def list_papers(keyword: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_data_available()
    try:
        from backend.rag.database import async_session_factory
        from backend.rag.models import Paper
        from backend.rag.search.sql_search import search_papers

        async with async_session_factory() as session:
            if keyword:
                return await search_papers(session, keyword, limit=limit)

            result = await session.execute(
                select(Paper)
                .where(Paper.review_status == "approved")
                .order_by(desc(Paper.year), desc(Paper.id))
                .limit(limit)
            )
            return [
                {
                    "type": "paper",
                    "id": paper.id,
                    "doi": paper.doi,
                    "title": paper.title,
                    "authors": paper.authors,
                    "journal": paper.journal,
                    "year": paper.year,
                    "summary": paper.summary,
                    "paper_type": paper.paper_type,
                }
                for paper in result.scalars()
            ]
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def paper_detail(paper_id: int) -> dict[str, Any]:
    _ensure_data_available()
    try:
        from backend.rag.database import async_session_factory
        from backend.rag.search.sql_search import get_paper_detail

        async with async_session_factory() as session:
            detail = await get_paper_detail(session, paper_id)
        if detail is None:
            raise RagNotFoundError("论文不存在")
        return detail
    except RagNotFoundError:
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def search_superconductors(
    formula: str | None = None,
    elements: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    _ensure_data_available()
    try:
        from backend.rag.database import async_session_factory
        from backend.rag.models import Superconductor
        from backend.rag.search.sql_search import search_by_elements_exact, search_by_formula

        async with async_session_factory() as session:
            if formula:
                return await search_by_formula(session, formula)
            if elements:
                parsed = [part.strip() for part in elements.replace(",", "-").split("-") if part.strip()]
                return await search_by_elements_exact(session, parsed)

            result = await session.execute(select(Superconductor).limit(limit))
            return [
                {
                    "type": "superconductor",
                    "id": sc.id,
                    "chemical_formula": sc.chemical_formula,
                    "formula_normalized": sc.formula_normalized,
                    "display_name": sc.display_name,
                    "composition": _loads_json(sc.composition, {}),
                    "element_ratio": _loads_json(sc.element_ratio, {}),
                }
                for sc in result.scalars()
            ]
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def superconductor_detail(superconductor_id: int) -> dict[str, Any]:
    _ensure_data_available()
    try:
        from backend.rag.database import async_session_factory
        from backend.rag.models import KeyProperty, Superconductor
        from backend.rag.search.sql_search import _format_property

        async with async_session_factory() as session:
            result = await session.execute(
                select(Superconductor)
                .where(Superconductor.id == superconductor_id)
                .options(
                    joinedload(Superconductor.chemical_system),
                    joinedload(Superconductor.key_properties).joinedload(KeyProperty.paper),
                )
            )
            sc = result.unique().scalar_one_or_none()
            if sc is None:
                raise RagNotFoundError("超导体不存在")

            return {
                "type": "superconductor",
                "id": sc.id,
                "chemical_system_id": sc.chemical_system_id,
                "chemical_system": sc.chemical_system.system_key if sc.chemical_system else None,
                "chemical_formula": sc.chemical_formula,
                "formula_normalized": sc.formula_normalized,
                "display_name": sc.display_name,
                "elements_list": _loads_json(sc.elements_list, []),
                "composition": _loads_json(sc.composition, {}),
                "element_ratio": _loads_json(sc.element_ratio, {}),
                "properties": [
                    _format_property(kp)
                    for kp in sc.key_properties
                    if kp.paper is None or kp.paper.review_status == "approved"
                ],
            }
    except RagNotFoundError:
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc


async def upload_pdf(file_path: Path, original_filename: str) -> dict[str, Any]:
    _ensure_chat_available()
    try:
        from backend.ingest.pipeline import ingest_pdf
    except ModuleNotFoundError as exc:
        raise RagInternalError("PDF 摄入模块尚未接入") from exc

    try:
        return await ingest_pdf(file_path=file_path, original_filename=original_filename)
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc
