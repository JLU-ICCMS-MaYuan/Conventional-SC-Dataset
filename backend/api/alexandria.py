"""
Alexandria 电声耦合数据库 API
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.services.alexandria_mysql import (
    query_by_elements, get_stats, get_material, get_cif,
    list_elements as mysql_list_elements,
)

router = APIRouter(prefix="/api/alexandria", tags=["alexandria"])


class AlexandriaSearchRequest(BaseModel):
    elements: List[str] = Field(..., description="元素符号列表")
    mode: str = Field("contains", description="筛选模式: only, combination, contains")
    min_tc: Optional[float] = Field(None, description="最低 Tc (K)")
    stable_only: bool = Field(False, description="仅稳定结构（无虚声子）")
    # 与前端筛选栏对齐的通用筛选参数
    tc_min: Optional[float] = Field(None, description="最低 Tc (K)，与 min_tc 等价且优先")
    tc_max: Optional[float] = Field(None, description="最高 Tc (K)")
    pressure_min: Optional[float] = Field(None, description="最低压强 (GPa)")
    pressure_max: Optional[float] = Field(None, description="最高压强 (GPa)")
    space_group_min: Optional[int] = Field(None, description="空间群编号下限")
    space_group_max: Optional[int] = Field(None, description="空间群编号上限")
    require_tc: bool = Field(False, description="仅返回有 Tc 数据的条目")
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
    tc_mcmillan: Optional[float] = None
    tc_allen_dynes: Optional[float] = None
    tc_eliashberg: Optional[float] = None
    wlog: Optional[float] = None
    integral_a2f: Optional[float] = None
    pressure: Optional[float] = None


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
        min_tc=request.tc_min if request.tc_min is not None else request.min_tc,
        max_tc=request.tc_max,
        pressure_min=request.pressure_min,
        pressure_max=request.pressure_max,
        spg_min=request.space_group_min,
        spg_max=request.space_group_max,
        require_tc=request.require_tc,
        stable_only=request.stable_only,
        limit=request.limit,
        offset=request.offset,
    )
    return result


@router.get("/elements")
def list_alexandria_elements():
    """列出 Alexandria 数据库中所有元素及其行范围"""
    try:
        return mysql_list_elements()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库未就绪: {e}")


@router.get("/material/{mat_id}")
def get_alexandria_material(mat_id: str):
    """获取材料原始数据（不含大矩阵，含轻量结构信息）"""
    data = get_material(mat_id)
    if not data:
        raise HTTPException(status_code=404, detail="材料未找到")
    return data


@router.get("/material/{mat_id}/download")
def download_alexandria_material(mat_id: str):
    """下载材料完整原始数据（含 force_constants 和 dyns，文件较大）"""
    from backend.services.alexandria_import import get_full_conn
    conn = get_full_conn()
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
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库未就绪: {e}")


@router.get("/material/{mat_id}/cif")
def get_alexandria_cif(mat_id: str):
    """获取材料的 CIF 结构文件（读预生成的 structure_cif 列）"""
    result = get_cif(mat_id)
    if not result:
        raise HTTPException(status_code=404, detail="材料未找到")
    if not result["cif"]:
        raise HTTPException(status_code=404, detail="该材料无结构信息")
    return Response(
        content=result["cif"],
        media_type="chemical/x-cif",
        headers={"Content-Disposition": f'inline; filename="{result["formula"] or mat_id}.cif"'}
    )
