"""
内部管理端点 — 供 Go 服务调用清理外部数据源

这些端点不暴露给前端，只接受来自 Go 服务的内部请求。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_admin
from models.user import User
from rag.vectordb import delete_paper_chunks
from rag.tools.neo4j import delete_paper_from_graph

router = APIRouter(prefix="/internal", tags=["internal"])


class DeletionResult(BaseModel):
    message: str
    deleted_count: int = 0


@router.delete("/papers/{paper_id}/vectors", response_model=DeletionResult)
async def delete_paper_vectors(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    """
    删除论文在 Qdrant 中的所有向量块。

    供 Go 服务在删除论文后调用。
    """
    try:
        delete_paper_chunks(paper_id)
        return DeletionResult(
            message=f"论文 {paper_id} 的向量已删除",
            deleted_count=0,  # Qdrant delete 不返回删除数量
        )
    except Exception as e:
        # 404 视为已删除，不抛出错误
        if "not found" in str(e).lower():
            return DeletionResult(
                message=f"论文 {paper_id} 的向量不存在（可能已删除）",
                deleted_count=0,
            )
        raise HTTPException(status_code=503, detail=f"Qdrant 清理失败: {str(e)}")


@router.delete("/papers/{paper_id}/graph", response_model=DeletionResult)
async def delete_paper_graph(
    paper_id: int,
    _current_user: User = Depends(get_current_admin),
):
    """
    删除论文在 Neo4j 中的节点和关系。

    供 Go 服务在删除论文后调用。
    """
    try:
        result = delete_paper_from_graph(paper_id)
        return DeletionResult(
            message=f"论文 {paper_id} 的图节点已删除",
            deleted_count=result.get("deleted_nodes", 0),
        )
    except Exception as e:
        # 404 视为已删除，不抛出错误
        if "not found" in str(e).lower():
            return DeletionResult(
                message=f"论文 {paper_id} 的图节点不存在（可能已删除）",
                deleted_count=0,
            )
        raise HTTPException(status_code=503, detail=f"Neo4j 清理失败: {str(e)}")
