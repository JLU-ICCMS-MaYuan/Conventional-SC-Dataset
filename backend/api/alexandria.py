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
BOHR_TO_A = 0.52917721067

IBRAV_NAMES = {
    1: "P 1", 2: "I 1", 3: "F 1",
    4: "P 6/mmm", 5: "R 3", 6: "P 4/mmm", 7: "I 4/mmm",
    8: "P mmm", 9: "C mmm", 10: "C mmm", 11: "C mmm",
    12: "P 2/m", 13: "C 2/m", 14: "P 1",
}


def _ibrav_to_lattice(ibrav, celldm):
    """根据 ibrav 和 celldm 计算晶格矢量（bohr）"""
    import math
    if not celldm or ibrav is None:
        return None
    a = celldm[0] if celldm[0] != 0 else 1.0
    # celldm(2)=b/a, celldm(3)=c/a 均为比值，需乘 a 得到绝对值
    b = a * celldm[1] if len(celldm) > 1 and celldm[1] != 0 else a
    c = a * celldm[2] if len(celldm) > 2 and celldm[2] != 0 else a
    cosab = celldm[3] if len(celldm) > 3 else 0.0
    cosac = celldm[4] if len(celldm) > 4 else 0.0
    cosbc = celldm[5] if len(celldm) > 5 else 0.0

    if ibrav == 1:
        return [[a, 0, 0], [0, a, 0], [0, 0, a]]
    elif ibrav == 2:
        return [[-a/2, a/2, a/2], [a/2, -a/2, a/2], [a/2, a/2, -a/2]]
    elif ibrav == 3:
        return [[0, a/2, a/2], [a/2, 0, a/2], [a/2, a/2, 0]]
    elif ibrav == 4:
        return [[a, 0, 0], [-a/2, a*math.sqrt(3)/2, 0], [0, 0, c]]
    elif ibrav == 5:
        tx = math.sqrt((1-cosab)/2); ty = math.sqrt((1-cosab)/6); tz = math.sqrt((1+2*cosab)/3)
        return [[a*tx, -a*ty, a*tz], [0, 2*a*ty, a*tz], [-a*tx, -a*ty, a*tz]]
    elif ibrav == 6:
        return [[a, 0, 0], [0, a, 0], [0, 0, c]]
    elif ibrav == 7:
        return [[a/2, -a/2, c/2], [a/2, a/2, -c/2], [-a/2, a/2, c/2]]
    elif ibrav == 8:
        return [[a, 0, 0], [0, b, 0], [0, 0, c]]
    elif ibrav in (9, 10, 11):
        return [[a/2, b/2, 0], [-a/2, b/2, 0], [0, 0, c]]
    elif ibrav == 12:
        return [[a, 0, 0], [b*cosab, b*math.sin(math.acos(cosab)), 0], [0, 0, c]]
    elif ibrav == 13:
        return [[a/2, 0, -c/2], [b*cosab, b*math.sin(math.acos(cosab)), 0], [a/2, 0, c/2]]
    elif ibrav == 14:
        sin_ab = math.sqrt(1 - cosab**2) if abs(cosab) < 1 else 0
        v1 = [a, 0, 0]; v2 = [b*cosab, b*sin_ab, 0]
        v3_x = c*cosac
        v3_y = c*(cosbc - cosab*cosac)/sin_ab if sin_ab > 1e-12 else 0
        v3_z = math.sqrt(max(0, c**2 - v3_x**2 - v3_y**2))
        return [v1, v2, [v3_x, v3_y, v3_z]]
    return None


def _lattice_params(lattice):
    """从晶格矢量计算 a,b,c,alpha,beta,gamma (angstrom, degree)"""
    import math
    v1, v2, v3 = lattice
    def _n(v): return math.sqrt(sum(x*x for x in v))
    a = _n(v1) * BOHR_TO_A
    b = _n(v2) * BOHR_TO_A
    c = _n(v3) * BOHR_TO_A
    def _ang(u, v):
        d = sum(x*y for x, y in zip(u, v))
        return math.degrees(math.acos(max(-1, min(1, d / (_n(u)*_n(v))))))
    return a, b, c, _ang(v2, v3), _ang(v1, v3), _ang(v1, v2)


def _structure_to_cif(ibrav, celldm, lattice, sites, formula):
    """将结构信息转为 CIF 格式文本"""
    if not lattice or not sites:
        return None
    from collections import Counter
    a, b, c, alpha, beta, gamma = _lattice_params(lattice)
    spg = IBRAV_NAMES.get(ibrav, "P 1")
    lines = [
        f"data_{formula or 'material'}",
        f"_symmetry_space_group_name_H-M   '{spg}'",
        f"_cell_length_a    {a:.6f}",
        f"_cell_length_b    {b:.6f}",
        f"_cell_length_c    {c:.6f}",
        f"_cell_angle_alpha {alpha:.4f}",
        f"_cell_angle_beta  {beta:.4f}",
        f"_cell_angle_gamma {gamma:.4f}",
        "loop_",
        "_atom_site_label",
        "_atom_site_type_symbol",
        "_atom_site_fract_x",
        "_atom_site_fract_y",
        "_atom_site_fract_z",
    ]
    cnt = Counter()
    for site in sites:
        el = site[0]
        cnt[el] += 1
        x = site[1] if len(site) > 1 else 0
        y = site[2] if len(site) > 2 else 0
        z = site[3] if len(site) > 3 else 0
        lines.append(f"  {el}{cnt[el]} {el} {x:.8f} {y:.8f} {z:.8f}")
    return "\n".join(lines)


def _extract_structure(data):
    """从 dyns 提取结构信息，不包含大矩阵"""
    dyns = data.get("dyns")
    if not dyns:
        return None
    ibrav = dyns.get("ibrav")
    celldm = dyns.get("celldm")
    sites = dyns.get("sites")
    species = dyns.get("species")
    if ibrav is None or not celldm:
        return None
    lattice = _ibrav_to_lattice(ibrav, celldm)
    cif = _structure_to_cif(ibrav, celldm, lattice, sites, data.get("formula", ""))
    return {
        "ibrav": ibrav,
        "celldm": celldm,
        "lattice": lattice,
        "sites": sites,
        "species": species,
        "cif": cif,
    }


@router.get("/material/{mat_id}")
def get_alexandria_material(mat_id: str):
    """获取材料原始数据（不含大矩阵，含轻量结构信息）"""
    from backend.alexandria_import import get_read_conn
    conn = get_read_conn()
    row = conn.execute(
        "SELECT data FROM entries WHERE mat_id = ?", (mat_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="材料未找到")
    data = json.loads(row[0])
    structure = _extract_structure(data)
    for field in HEAVY_FIELDS:
        data.pop(field, None)
    if structure:
        data["structure"] = structure
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


@router.get("/material/{mat_id}/cif")
def get_alexandria_cif(mat_id: str):
    """获取材料的 CIF 结构文件"""
    from backend.alexandria_import import get_read_conn
    conn = get_read_conn()
    row = conn.execute(
        "SELECT data FROM entries WHERE mat_id = ?", (mat_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="材料未找到")
    data = json.loads(row[0])
    structure = _extract_structure(data)
    if not structure or not structure.get("cif"):
        raise HTTPException(status_code=404, detail="该材料无结构信息")
    formula = data.get("formula", mat_id)
    return Response(
        content=structure["cif"],
        media_type="chemical/x-cif",
        headers={"Content-Disposition": f'inline; filename="{formula}.cif"'}
    )
