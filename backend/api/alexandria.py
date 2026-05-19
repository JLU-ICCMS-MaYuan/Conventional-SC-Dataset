"""
Alexandria 电声耦合数据库 API
"""
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.alexandria_import import query_by_elements

router = APIRouter(prefix="/api/alexandria", tags=["alexandria"])


class AlexandriaSearchRequest(BaseModel):
    elements: List[str] = Field(..., description="元素符号列表")
    mode: str = Field("contains", description="筛选模式: only, combination, contains")
    min_tc: Optional[float] = Field(None, description="最低 Tc (K)")
    stable_only: bool = Field(False, description="仅稳定结构（无虚声子）")
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class AlexandriaMaterial(BaseModel):
    id: int
    mat_id: str
    formula: str
    elements: List[str]
    nsites: Optional[int] = None
    spg: Optional[int] = None
    lambda_val: Optional[float] = None
    tc_max: Optional[float] = None
    imag: bool = True
    band_gap: Optional[float] = None
    dos_ef: Optional[float] = None


class AlexandriaSearchResult(BaseModel):
    items: List[dict]
    total: int
    has_prev: bool
    has_next: bool


@router.post("/search", response_model=AlexandriaSearchResult)
def search_alexandria(request: AlexandriaSearchRequest):
    """按元素搜索 Alexandria 数据库中的材料"""
    if not request.elements:
        raise HTTPException(status_code=400, detail="至少需要选择一个元素")

    result = query_by_elements(
        elements=request.elements,
        mode=request.mode,
        min_tc=request.min_tc,
        stable_only=request.stable_only,
        limit=request.limit,
        offset=request.offset,
    )
    return result


@router.get("/elements")
def list_alexandria_elements():
    """列出 Alexandria 数据库中所有元素及其行范围"""
    try:
        from backend.alexandria_import import get_read_conn
        conn = get_read_conn()
        cur = conn.execute("""
            SELECT element, MIN(entry_id), MAX(entry_id), COUNT(*)
            FROM element_idx GROUP BY element ORDER BY element
        """)
        rows = [{"element": r[0], "min_row": r[1], "max_row": r[2], "count": r[3]} for r in cur.fetchall()]
        return {"items": rows, "total": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库未就绪: {e}")


HEAVY_FIELDS = {"force_constants", "dyns", "a2f", "broadening"}


@router.get("/material/{mat_id}")
def get_alexandria_material(mat_id: str):
    """获取材料原始数据（不含 force_constants 和 dyns，减小响应体积）"""
    from backend.alexandria_import import get_read_conn
    conn = get_read_conn()
    row = conn.execute(
        "SELECT data FROM entries WHERE mat_id = ?", (mat_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="材料未找到")
    data = json.loads(row[0])
    for field in HEAVY_FIELDS:
        data.pop(field, None)
    return data


@router.get("/material/{mat_id}/download")
def download_alexandria_material(mat_id: str):
    """下载材料完整原始数据（含 force_constants 和 dyns，文件较大）"""
    from backend.alexandria_import import get_read_conn
    conn = get_read_conn()
    row = conn.execute(
        "SELECT data FROM entries WHERE mat_id = ?", (mat_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="材料未找到")
    data = json.loads(row[0])
    formula = data.get("formula", mat_id)
    filename = f"{formula}_{mat_id}.json"
    return Response(
        content=row[0],
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/stats")
def alexandria_stats():
    """返回 Alexandria 数据库统计信息"""
    try:
        from backend.alexandria_import import get_read_conn
        conn = get_read_conn()
        total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        with_tc = conn.execute("SELECT COUNT(*) FROM entries WHERE tc_max IS NOT NULL").fetchone()[0]
        stable = conn.execute("SELECT COUNT(*) FROM entries WHERE imag = 0").fetchone()[0]
        return {"total_entries": total, "with_tc": with_tc, "stable": stable}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库未就绪: {e}")
