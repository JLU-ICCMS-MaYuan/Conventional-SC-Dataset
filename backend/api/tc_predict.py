"""
Tc 预测 API
"""
from typing import List, Tuple, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
from pymatgen.core import Structure
from io import BytesIO

from backend import schemas

router = APIRouter(prefix="/api/tc-predict", tags=["tc-predict"])

BOND_THRESHOLD = 1.4
COUPLING_RANGE = (0.98, 1.28)
SLOPE1 = 16370.6
SLOPE2 = 24.7
MAX_METAL_FILES = 4


def _load_structure(content: bytes) -> Structure:
    """解析 CONTCAR 内容"""
    try:
        text = content.decode("utf-8", errors="ignore")
        return Structure.from_str(text, fmt="poscar")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法解析 CONTCAR: {exc}") from exc


def _extract_h_sublattice(structure: Structure) -> Tuple[List[float], int, float]:
    """获取 H-H 键长等特征"""
    composition = structure.composition.reduced_composition
    h_per_formula = composition.get_el_amt_dict().get("H", 0)
    if h_per_formula == 0:
        raise HTTPException(status_code=400, detail="结构中未找到 H 原子，无法计算 Tc")

    h_only = structure.copy()
    species_to_remove = [sp for sp in structure.symbol_set if sp != "H"]
    h_only.remove_species(species_to_remove)

    h_atoms = len(h_only)
    if h_atoms == 0:
        raise HTTPException(status_code=400, detail="未能提取出 H 原子，请检查结构文件")

    dist_mat = h_only.distance_matrix
    bonds: List[float] = []
    for i in range(h_atoms):
        for j in range(i):
            distance = float(dist_mat[i][j])
            if distance <= BOND_THRESHOLD:
                bonds.append(distance)

    if not bonds:
        raise HTTPException(status_code=400, detail="未找到 1.4 Å 以内的 H-H 键，请检查结构")

    super_cell = h_atoms / h_per_formula
    if not float(super_cell).is_integer():
        raise HTTPException(status_code=400, detail="结构的 H 个数与化学式不匹配，请确认超胞倍数")

    return bonds, h_atoms, super_cell


def _read_pdos_value(content: bytes) -> float:
    """读取 PDOS 文件的费米能态密度"""
    data = None
    for loader in (np.loadtxt, np.genfromtxt):
        try:
            buffer = BytesIO(content)
            data = loader(buffer)
            break
        except Exception:
            data = None
    if data is None:
        raise HTTPException(status_code=400, detail="无法解析 PDOS 数据")
    if data.ndim < 2 or data.shape[1] < 2:
        raise HTTPException(status_code=400, detail="PDOS 文件列数不足")
    energies = data[:, 0]
    dos_values = data[:, -1]
    idx = int(np.argmin(np.abs(energies)))
    return float(dos_values[idx])


def _normalize_bonds(bonds: List[float], atoms: int) -> Dict[float, float]:
    counts: Dict[float, float] = {}
    for value in bonds:
        rounded = np.floor(value * 1000) / 1000
        counts[rounded] = counts.get(rounded, 0.0) + 1.0
    return {k: v / atoms for k, v in sorted(counts.items())}


def _calculate_coupling(bond_distribution: Dict[float, float], dos_h_atom_bond: float) -> float:
    bl, br = COUPLING_RANGE
    couple = 0.0
    for length, frac in bond_distribution.items():
        weight = 1.0 if bl <= length <= br else 0.0
        couple += length * frac * dos_h_atom_bond * weight
    return couple


@router.post("/", response_model=schemas.TcPredictionResponse)
async def predict_tc(
    contcar: UploadFile = File(..., description="VASP CONTCAR 文件"),
    pdos_files: List[UploadFile] = File(..., description="包含 PDOS_H 在内的 PDOS 数据文件")
):
    """
    上传 CONTCAR + PDOS 计算 Tc（实验页面）
    """
    if not pdos_files:
        raise HTTPException(status_code=400, detail="请至少上传一个 PDOS 文件（需要包含 PDOS_H.dat）")

    structure = _load_structure(await contcar.read())
    bonds, h_atoms, _ = _extract_h_sublattice(structure)

    h_value = None
    metal_values: List[float] = []
    for upload in pdos_files:
        content = await upload.read()
        value = _read_pdos_value(content)
        filename = (upload.filename or "").upper()
        if "PDOS_H" in filename or filename.endswith("H.DAT"):
            if h_value is None:
                h_value = value
        else:
            metal_values.append(value)

    if h_value is None:
        raise HTTPException(status_code=400, detail="缺少 PDOS_H.dat 文件，请重新上传")

    # 补齐/截断 4 个金属 PDOS 值
    metal_values = (metal_values + [0.0] * MAX_METAL_FILES)[:MAX_METAL_FILES]

    total_metal = sum(metal_values)
    if (h_value + total_metal) == 0:
        raise HTTPException(status_code=400, detail="PDOS 数值为 0，无法计算 Tc")

    bond_distribution = _normalize_bonds(bonds, h_atoms)
    bonds_num_atom = sum(bond_distribution.values())
    if bonds_num_atom == 0:
        raise HTTPException(status_code=400, detail="无法计算键长分布")

    dos_h_atom = h_value / h_atoms
    dos_h_atom_bond = dos_h_atom / bonds_num_atom
    dos_h_ratio = h_value / (h_value + total_metal)
    couple = _calculate_coupling(bond_distribution, dos_h_atom_bond)
    denominator = 1 + dos_h_ratio ** 2
    f2 = (dos_h_ratio * couple) / denominator if denominator else 0
    predicted_tc = SLOPE1 * f2 + SLOPE2

    return schemas.TcPredictionResponse(
        predicted_tc=round(predicted_tc, 3),
        f2_value=round(f2, 6),
        dos_h_ratio=round(dos_h_ratio, 6),
        dos_h_atom_bond=round(dos_h_atom_bond, 6),
        bonds_mean=round(float(np.mean(bonds)), 6),
        bonds_var=round(float(np.var(bonds)), 6)
    )
