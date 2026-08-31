"""
内部管理端点 — 供 Go 服务在物理删除论文后清理外部数据源。

这些端点不面向前端：Go 在 MySQL 事务提交成功后调用它们清理 Qdrant 与 Neo4j。
清理属 best-effort，Go 侧失败只记日志，因此这里对「目标本就不存在」一律返回成功，
避免把幂等重试变成错误。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models import User
from backend.security import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["internal"])


class DeletionResult(BaseModel):
    message: str
    deleted_count: int = 0


@router.delete("/papers/{paper_id}/vectors", response_model=DeletionResult)
async def delete_paper_vectors(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
) -> DeletionResult:
    """删除论文在 Qdrant 中的所有向量块。"""
    from backend.rag.vectordb import delete_paper_chunks

    try:
        delete_paper_chunks(paper_id)
    except Exception as exc:  # noqa: BLE001 — 外部依赖异常类型不稳定
        logger.warning("Qdrant 清理失败 paper_id=%s: %s", paper_id, exc)
        raise HTTPException(status_code=503, detail={
            "code": "qdrant_cleanup_failed",
            "message": "向量库清理失败，论文数据库记录已删除，请稍后重试清理",
        }) from exc

    return DeletionResult(message=f"论文 {paper_id} 的向量已删除")


@router.delete("/papers/{paper_id}/graph", response_model=DeletionResult)
async def delete_paper_graph(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
) -> DeletionResult:
    """删除论文在 Neo4j 中的节点及其全部关系。"""
    from backend.rag.tools.neo4j import delete_paper_from_graph

    try:
        result = delete_paper_from_graph(paper_id)
    except Exception as exc:  # noqa: BLE001 — 外部依赖异常类型不稳定
        logger.warning("Neo4j 清理失败 paper_id=%s: %s", paper_id, exc)
        raise HTTPException(status_code=503, detail={
            "code": "neo4j_cleanup_failed",
            "message": "图数据库清理失败，论文数据库记录已删除，请稍后重试清理",
        }) from exc

    return DeletionResult(
        message=result.get("message", f"论文 {paper_id} 的图节点已删除"),
        deleted_count=result.get("deleted_nodes", 0),
    )
