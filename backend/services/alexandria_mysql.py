"""
Alexandria 电声耦合数据库 MySQL 查询模块
数据由 backend/scripts/migrate_alexandria_to_mysql.py 从 SQLite 迁移（仅含有 Tc 的条目），
spg/stress/data_json 由 backend/scripts/backfill_alexandria_structure.py 补全
"""
import json
import math
from typing import Dict, List, Optional

from sqlalchemy import text

from backend.database import engine

BOHR_TO_A = 0.52917721067

# 元素符号 → 原子序数（'X' 为 0 号占位）
_ELEMENT_SYMBOLS = [
    'X', 'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg',
    'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn',
    'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb',
    'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In',
    'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm',
    'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta',
    'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At',
    'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu',
]
ELEMENT_Z = {s: i for i, s in enumerate(_ELEMENT_SYMBOLS)}

# data_json 中剥离的大字段（详情/结构预览不需要）
HEAVY_FIELDS = {"force_constants", "a2f", "broadening"}

# 压强由应力张量换算：P = -(sxx+syy+szz)/3 * 0.1（kbar → GPa）
_PRESSURE_SQL = "(-(e.stress_xx + e.stress_yy + e.stress_zz) / 3.0 * 0.1)"
_STRESS_NOT_NULL = "e.stress_xx IS NOT NULL AND e.stress_yy IS NOT NULL AND e.stress_zz IS NOT NULL"


def query_by_elements(elements: List[str], mode: str = "contains",
                      min_tc: Optional[float] = None, stable_only: bool = False,
                      max_tc: Optional[float] = None, pressure_min: Optional[float] = None,
                      pressure_max: Optional[float] = None, spg_min: Optional[int] = None,
                      spg_max: Optional[int] = None, require_tc: bool = False,
                      limit: int = 50, offset: int = 0) -> Dict:
    """按元素查询材料（集合语义：only=等于查询集, combination=条目元素⊆查询集, contains=条目包含全部查询元素）"""
    elements = sorted(set(elements))
    if not elements:
        return {"items": [], "total": 0, "has_prev": False, "has_next": False}

    el_params = {f"el{i}": el for i, el in enumerate(elements)}
    placeholders = ",".join(f":{k}" for k in el_params)

    # 包含全部查询元素的候选集（元素索引表 GROUP BY 计数）
    contains_sub = (
        f"SELECT entry_id FROM alexandria_element_idx "
        f"WHERE element IN ({placeholders}) "
        f"GROUP BY entry_id HAVING COUNT(DISTINCT element) = :n_els"
    )
    # 条目不含查询集之外的元素（子集条件）
    subset_cond = (
        f"NOT EXISTS (SELECT 1 FROM alexandria_element_idx x "
        f"WHERE x.entry_id = e.id AND x.element NOT IN ({placeholders}))"
    )
    if mode == "contains":
        candidate = f"e.id IN ({contains_sub})"
    elif mode == "combination":
        candidate = (
            f"e.id IN (SELECT DISTINCT entry_id FROM alexandria_element_idx "
            f"WHERE element IN ({placeholders})) AND {subset_cond}"
        )
    elif mode == "only":
        candidate = f"e.id IN ({contains_sub}) AND {subset_cond}"
    else:
        return {"items": [], "total": 0, "has_prev": False, "has_next": False}

    filters = [candidate]
    params: Dict = {**el_params, "n_els": len(elements)}
    if min_tc is not None:
        filters.append("e.tc_max >= :min_tc")
        params["min_tc"] = min_tc
    if max_tc is not None:
        filters.append("e.tc_max <= :max_tc")
        params["max_tc"] = max_tc
    if require_tc:
        filters.append("(e.tc_max IS NOT NULL OR e.tc_allen_dynes IS NOT NULL)")
    if spg_min is not None:
        filters.append("e.spg >= :spg_min")
        params["spg_min"] = spg_min
    if spg_max is not None:
        filters.append("e.spg <= :spg_max")
        params["spg_max"] = spg_max
    if pressure_min is not None:
        filters.append(f"({_STRESS_NOT_NULL} AND {_PRESSURE_SQL} >= :p_min)")
        params["p_min"] = pressure_min
    if pressure_max is not None:
        filters.append(f"({_STRESS_NOT_NULL} AND {_PRESSURE_SQL} <= :p_max)")
        params["p_max"] = pressure_max
    if stable_only:
        filters.append("e.imag = 0")
    where = " AND ".join(filters)

    with engine.connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM alexandria_entries e WHERE {where}"), params
        ).scalar() or 0
        rows = conn.execute(text(f"""
            SELECT e.id, e.mat_id, e.formula, e.elements, e.nsites, e.spg,
                   e.lambda_val, e.tc_max, e.imag, e.band_gap, e.dos_ef,
                   e.tc_mcmillan, e.tc_allen_dynes, e.tc_eliashberg,
                   e.wlog, e.integral_a2f,
                   e.stress_xx, e.stress_yy, e.stress_zz
            FROM alexandria_entries e WHERE {where}
            ORDER BY e.tc_max IS NULL, e.tc_max DESC
            LIMIT :limit OFFSET :offset
        """), {**params, "limit": limit, "offset": offset}).fetchall()

    items = []
    for r in rows:
        sxx, syy, szz = r[16], r[17], r[18]
        if sxx is not None and syy is not None and szz is not None:
            pressure = round(-(sxx + syy + szz) / 3.0 * 0.1, 2)
        else:
            pressure = None
        items.append({
            "id": r[0], "mat_id": r[1], "formula": r[2],
            "elements": json.loads(r[3]) if r[3] else [],
            "nsites": r[4], "spg": r[5],
            "lambda_val": r[6], "tc_max": r[7], "imag": bool(r[8]),
            "band_gap": r[9], "dos_ef": r[10],
            "tc_mcmillan": r[11], "tc_allen_dynes": r[12],
            "tc_eliashberg": r[13], "wlog": r[14], "integral_a2f": r[15],
            "pressure": pressure,
        })

    return {
        "items": items,
        "total": total,
        "has_prev": offset > 0,
        "has_next": offset + limit < total,
    }


def get_stats() -> Dict:
    """返回 Alexandria MySQL 库统计信息"""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM alexandria_entries")).scalar()
        with_tc = conn.execute(text("SELECT COUNT(*) FROM alexandria_entries WHERE tc_max IS NOT NULL")).scalar()
        stable = conn.execute(text("SELECT COUNT(*) FROM alexandria_entries WHERE imag = 0")).scalar()
    return {"total_entries": total, "with_tc": with_tc, "stable": stable}


def list_elements() -> Dict:
    """列出库中所有元素及其行范围"""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT element, MIN(entry_id), MAX(entry_id), COUNT(*)
            FROM alexandria_element_idx GROUP BY element ORDER BY element
        """)).fetchall()
    items = [{"element": r[0], "min_row": r[1], "max_row": r[2], "count": r[3]} for r in rows]
    return {"items": items, "total": len(items)}


# ── 结构解析工具（QE dyn 数据 → 晶格/空间群/CIF）──

def ibrav_to_lattice(ibrav, celldm):
    """根据 QE ibrav 和 celldm 计算晶格矢量（bohr），支持 -12/-13 单斜变体"""
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
        return [[-a/2, 0, a/2], [0, a/2, a/2], [-a/2, a/2, 0]]
    elif ibrav == 3:
        return [[a/2, a/2, a/2], [-a/2, a/2, a/2], [-a/2, -a/2, a/2]]
    elif ibrav == 4:
        return [[a, 0, 0], [-a/2, a*math.sqrt(3)/2, 0], [0, 0, c]]
    elif ibrav == 5:
        tx = math.sqrt((1-cosab)/2); ty = math.sqrt((1-cosab)/6); tz = math.sqrt((1+2*cosab)/3)
        return [[a*tx, -a*ty, a*tz], [0, 2*a*ty, a*tz], [-a*tx, -a*ty, a*tz]]
    elif ibrav == 6:
        return [[a, 0, 0], [0, a, 0], [0, 0, c]]
    elif ibrav == 7:
        return [[a/2, -a/2, c/2], [a/2, a/2, c/2], [-a/2, -a/2, c/2]]
    elif ibrav == 8:
        return [[a, 0, 0], [0, b, 0], [0, 0, c]]
    elif ibrav == 9:
        return [[a/2, b/2, 0], [-a/2, b/2, 0], [0, 0, c]]
    elif ibrav == 10:
        # 面心正交
        return [[a/2, 0, c/2], [a/2, b/2, 0], [0, b/2, c/2]]
    elif ibrav == 11:
        # 体心正交
        return [[a/2, b/2, c/2], [-a/2, b/2, c/2], [-a/2, -b/2, c/2]]
    elif ibrav == 12:
        sinab = math.sqrt(max(0.0, 1 - cosab**2))
        return [[a, 0, 0], [b*cosab, b*sinab, 0], [0, 0, c]]
    elif ibrav == -12:
        # 单斜 P，unique axis b（celldm(5)=cos(ac)）
        sinac = math.sqrt(max(0.0, 1 - cosac**2))
        return [[a, 0, 0], [0, b, 0], [c*cosac, 0, c*sinac]]
    elif ibrav == 13:
        sinab = math.sqrt(max(0.0, 1 - cosab**2))
        return [[a/2, 0, -c/2], [b*cosab, b*sinab, 0], [a/2, 0, c/2]]
    elif ibrav == -13:
        # 底心单斜，unique axis b
        sinac = math.sqrt(max(0.0, 1 - cosac**2))
        return [[a/2, b/2, 0], [-a/2, b/2, 0], [c*cosac, 0, c*sinac]]
    elif ibrav == 14:
        sin_ab = math.sqrt(1 - cosab**2) if abs(cosab) < 1 else 0
        v1 = [a, 0, 0]; v2 = [b*cosab, b*sin_ab, 0]
        v3_x = c*cosac
        v3_y = c*(cosbc - cosab*cosac)/sin_ab if sin_ab > 1e-12 else 0
        v3_z = math.sqrt(max(0, c**2 - v3_x**2 - v3_y**2))
        return [v1, v2, [v3_x, v3_y, v3_z]]
    return None


def sites_to_fractional(lattice, sites, alat):
    """QE dyn 的 sites 坐标为 cartesian（alat 单位），转为分数坐标"""
    import numpy as np
    L = np.array(lattice, dtype=float)
    cart = np.array([[float(s[1]), float(s[2]), float(s[3])] for s in sites]) * (alat or 1.0)
    frac = cart @ np.linalg.inv(L)
    return (frac % 1.0).tolist()


def compute_structure(data: dict) -> Optional[dict]:
    """从 data['dyns'] 解析结构：晶格、分数坐标、spglib 空间群

    Returns:
        {"lattice": bohr 晶格, "frac_coords": 分数坐标, "numbers": 原子序数,
         "symbols": 元素符号, "spg_number": int|None, "spg_symbol": str|None} 或 None
    """
    dyns = data.get("dyns") or {}
    ibrav, celldm, sites = dyns.get("ibrav"), dyns.get("celldm"), dyns.get("sites")
    lattice = ibrav_to_lattice(ibrav, celldm)
    if not lattice or not sites:
        return None
    alat = celldm[0] if celldm and celldm[0] else 1.0
    frac = sites_to_fractional(lattice, sites, alat)
    symbols = [s[0] for s in sites]
    numbers = [ELEMENT_Z.get(sym, 0) for sym in symbols]

    spg_number, spg_symbol = None, None
    try:
        import spglib
        best = None
        # symprec 梯度：DFT 弛豫结构常需放宽容差才能识别理想对称性
        for prec in (1e-3, 1e-2, 0.1):
            ds = spglib.get_symmetry_dataset((lattice, frac, numbers), symprec=prec)
            if ds and (best is None or ds.number > best.number):
                best = ds
        if best:
            spg_number, spg_symbol = int(best.number), str(best.international)
    except Exception:
        pass
    return {
        "lattice": lattice, "frac_coords": frac, "numbers": numbers,
        "symbols": symbols, "spg_number": spg_number, "spg_symbol": spg_symbol,
    }


def strip_heavy(data: dict) -> dict:
    """剥离大矩阵字段，返回适合入库/传输的轻量副本"""
    slim = {k: v for k, v in data.items() if k not in HEAVY_FIELDS}
    if isinstance(slim.get("dyns"), dict):
        slim["dyns"] = {k: v for k, v in slim["dyns"].items() if k != "dyn"}
    return slim


def extract_pressure_gpa(data: dict) -> Optional[float]:
    """stress 为 Voigt 记法 [sxx, syy, szz, ...]（kbar），换算为 GPa"""
    stress = data.get("stress")
    if not isinstance(stress, list) or len(stress) < 3:
        return None
    try:
        return round(-(stress[0] + stress[1] + stress[2]) / 3.0 * 0.1, 6)
    except TypeError:
        return None


def _lattice_params_angstrom(lattice):
    """从晶格矢量（bohr）计算 a,b,c（Å）与 α,β,γ（度）"""
    v1, v2, v3 = lattice
    def _n(v): return math.sqrt(sum(x*x for x in v))
    def _ang(u, v):
        d = sum(x*y for x, y in zip(u, v))
        return math.degrees(math.acos(max(-1, min(1, d / (_n(u)*_n(v))))))
    return (_n(v1)*BOHR_TO_A, _n(v2)*BOHR_TO_A, _n(v3)*BOHR_TO_A,
            _ang(v2, v3), _ang(v1, v3), _ang(v1, v2))


def structure_to_cif(structure: dict, formula: str) -> Optional[str]:
    """将 compute_structure 结果转为 CIF 文本（分数坐标）"""
    if not structure:
        return None
    from collections import Counter
    a, b, c, alpha, beta, gamma = _lattice_params_angstrom(structure["lattice"])
    lines = [
        f"data_{formula or 'material'}",
        f"_symmetry_space_group_name_H-M   '{structure.get('spg_symbol') or 'P 1'}'",
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
    for sym, (x, y, z) in zip(structure["symbols"], structure["frac_coords"]):
        cnt[sym] += 1
        lines.append(f"  {sym}{cnt[sym]} {sym} {x:.8f} {y:.8f} {z:.8f}")
    return "\n".join(lines)


def get_material(mat_id: str) -> Optional[dict]:
    """按 mat_id 读取轻量原始数据（data_json），附带结构信息（CIF 读预生成列）"""
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT data_json, formula, spg, structure_cif "
            "FROM alexandria_entries WHERE mat_id = :m"
        ), {"m": mat_id}).fetchone()
    if not row or not row[0]:
        return None
    data = json.loads(row[0])
    structure = compute_structure(data)
    if structure:
        data["structure"] = {
            "ibrav": (data.get("dyns") or {}).get("ibrav"),
            "celldm": (data.get("dyns") or {}).get("celldm"),
            "lattice": structure["lattice"],
            "sites": (data.get("dyns") or {}).get("sites"),
            "species": (data.get("dyns") or {}).get("species"),
            "spg_number": structure["spg_number"],
            "spg_symbol": structure["spg_symbol"],
            "cif": row[3] or structure_to_cif(structure, row[1]),
        }
    return data


def get_cif(mat_id: str) -> Optional[dict]:
    """按 mat_id 读取预生成的 CIF 文本"""
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT structure_cif, formula FROM alexandria_entries WHERE mat_id = :m"
        ), {"m": mat_id}).fetchone()
    if not row:
        return None
    return {"cif": row[0], "formula": row[1]}
