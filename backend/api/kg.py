"""RAG 知识图谱 API — 前端/Agent 调用入口，逻辑委托给 backend.rag.tools.neo4j"""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from backend.rag.tools.neo4j import (
    search_papers,
    get_paper_context,
    get_material_context,
    traverse_graph,
    find_path,
)

router = APIRouter(prefix="/api/kg", tags=["kg"])


@router.get("/traverse")
def traverse(
    paper_id: int = Query(..., description="起点论文ID"),
    depth: int = Query(2, ge=1, le=4, description="遍历深度"),
    relation: str | None = Query(None, description="限定关系类型，逗号分隔"),
    limit: int = Query(20, ge=1, le=100),
):
    """从论文出发，多跳遍历关联论文和材料"""
    return traverse_graph(paper_id, depth=depth, relations=relation, limit=limit)


@router.get("/path")
def shortest_path(
    from_paper: int = Query(...),
    to_paper: int = Query(...),
    max_depth: int = Query(4, ge=1, le=6),
):
    """两篇论文之间的最短发展路径"""
    result = find_path(from_paper, to_paper, max_depth=max_depth)
    if "message" in result and not result["path"]:
        return result
    return result


@router.get("/around")
def around_paper(
    paper_id: int = Query(...),
    relations: str | None = Query(None, description="逗号分隔，如 STUDIES,RELATES_TO"),
):
    """一篇论文的上下文：研究的材料 + 关联论文 + 前驱工作 + 作者"""
    ctx = get_paper_context(paper_id)
    if "error" in ctx:
        raise HTTPException(404, ctx["error"])

    # 按 relations 参数过滤
    if relations:
        allowed = set(relations.split(","))
        if "RELATES_TO" not in allowed:
            ctx.pop("related_papers", None)
        if "STUDIES" not in allowed:
            ctx.pop("materials", None)
        if "BUILDS_ON" not in allowed:
            ctx.pop("builds_on", None)
        if "AUTHORED" not in allowed:
            ctx.pop("authors", None)

    return ctx


@router.get("/material/{formula}")
def material_context(formula: str):
    """材料上下文：哪些论文研究过、关键参数"""
    return get_material_context(formula)


@router.get("/search")
def kg_search(
    q: str = Query(..., description="搜索词：论文标题/材料化学式/作者名"),
    limit: int = Query(10, ge=1, le=50),
):
    """模糊搜索：匹配论文标题"""
    return search_papers(q, limit=limit)
