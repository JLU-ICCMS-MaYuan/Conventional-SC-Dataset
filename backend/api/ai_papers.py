"""
Deprecated AI-paper database routes.

The redesigned site no longer separates search results by local/AI database.
Keep this module importable so older tooling fails with a clear API response.
"""

from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/api/ai/papers", tags=["ai-papers"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def ai_papers_deprecated(path: str):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="AI 论文双数据库入口已下线；请使用统一的 /api/papers 和 /api/compounds/search。",
    )
