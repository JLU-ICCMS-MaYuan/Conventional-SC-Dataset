"""结构候选的确定性校验、标准化、等价比较和格式导出。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Any, Literal

from ase import Atoms
from ase.io import read as ase_read
from ase.io import write as ase_write


CellKind = Literal["primitive", "conventional"]
StructureFormat = Literal["cif", "poscar"]


class StructureCandidateError(ValueError):
    """结构候选无法安全构造或验证时抛出的可展示错误。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class StructureValidation:
    structure_format: str
    structure_hash: str
    atom_count: int
    elements: tuple[str, ...]
    cell_parameters: dict[str, float]
    volume: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "structure_format": self.structure_format,
            "structure_hash": self.structure_hash,
            "atom_count": self.atom_count,
            "elements": list(self.elements),
            "cell_parameters": dict(self.cell_parameters),
            "volume": self.volume,
            "ase_valid": True,
        }


def normalize_structure_format(value: str) -> StructureFormat:
    normalized = str(value or "").strip().lower().lstrip(".")
    if normalized in {"cif"}:
        return "cif"
    if normalized in {"poscar", "vasp", "contcar"}:
        return "poscar"
    raise StructureCandidateError(
        "structure_format_invalid",
        "结构格式必须是 CIF 或 POSCAR",
    )


def _ase_format(value: StructureFormat) -> str:
    return "cif" if value == "cif" else "vasp"


def read_atoms(structure_format: str, structure_text: str) -> Atoms:
    normalized = normalize_structure_format(structure_format)
    if not str(structure_text or "").strip():
        raise StructureCandidateError("structure_text_empty", "结构内容不能为空")
    try:
        atoms = ase_read(
            StringIO(str(structure_text)),
            format=_ase_format(normalized),
            index=0,
        )
    except Exception as exc:  # ASE exposes format-specific parser exceptions.
        raise StructureCandidateError(
            "structure_parse_failed",
            f"无法解析 {normalized.upper()} 结构内容",
        ) from exc
    if not isinstance(atoms, Atoms) or len(atoms) == 0:
        raise StructureCandidateError("structure_empty", "结构不包含原子")
    if atoms.cell.volume <= 0:
        raise StructureCandidateError("structure_cell_invalid", "结构晶胞体积必须大于 0")
    return atoms


def validate_atoms(atoms: Atoms, structure_format: str, *, source_text: str | None = None) -> StructureValidation:
    normalized = normalize_structure_format(structure_format)
    cellpar = atoms.cell.cellpar()
    canonical_text = source_text.strip() if source_text is not None else serialize_atoms(atoms, normalized)
    return StructureValidation(
        structure_format=normalized,
        structure_hash=hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
        atom_count=len(atoms),
        elements=tuple(sorted(set(atoms.get_chemical_symbols()))),
        cell_parameters={
            "a": float(cellpar[0]),
            "b": float(cellpar[1]),
            "c": float(cellpar[2]),
            "alpha": float(cellpar[3]),
            "beta": float(cellpar[4]),
            "gamma": float(cellpar[5]),
        },
        volume=float(atoms.get_volume()),
    )


def validate_structure_text(structure_format: str, structure_text: str) -> dict[str, Any]:
    normalized = normalize_structure_format(structure_format)
    atoms = read_atoms(normalized, structure_text)
    return validate_atoms(atoms, normalized, source_text=structure_text).as_dict()


def serialize_atoms(atoms: Atoms, structure_format: str) -> str:
    normalized = normalize_structure_format(structure_format)
    # ASE 的 CIF writer 会自行包装并 detach 二进制流；POSCAR writer 则接受文本流。
    stream = BytesIO() if normalized == "cif" else StringIO()
    try:
        ase_write(stream, atoms, format=_ase_format(normalized))
    except Exception as exc:
        raise StructureCandidateError(
            "structure_export_failed",
            f"无法导出 {normalized.upper()} 结构内容",
        ) from exc
    value = stream.getvalue()
    text = value.decode("latin-1") if isinstance(value, bytes) else value
    if not text.strip():
        raise StructureCandidateError("structure_export_empty", "结构导出结果为空")
    return text


def _pymatgen_structure(atoms: Atoms):
    try:
        from pymatgen.io.ase import AseAtomsAdaptor

        return AseAtomsAdaptor.get_structure(atoms)
    except Exception as exc:
        raise StructureCandidateError(
            "structure_standardization_failed",
            "无法将结构转换为晶体学标准化对象",
        ) from exc


def _as_ase(structure) -> Atoms:
    try:
        from pymatgen.io.ase import AseAtomsAdaptor

        return AseAtomsAdaptor.get_atoms(structure)
    except Exception as exc:
        raise StructureCandidateError(
            "structure_standardization_failed",
            "无法将标准化结构转换为 ASE 对象",
        ) from exc


def standardize_cells(atoms: Atoms) -> dict[CellKind, tuple[Atoms, str]]:
    """生成原胞和惯用胞；识别失败时保守地返回原结构并标记原因。"""
    structure = _pymatgen_structure(atoms)
    try:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        analyzer = SpacegroupAnalyzer(structure, symprec=1e-3, angle_tolerance=5)
        conventional = _as_ase(analyzer.get_conventional_standard_structure())
        primitive = _as_ase(analyzer.get_primitive_standard_structure())
        return {
            "primitive": (primitive, "pymatgen.get_primitive_standard_structure"),
            "conventional": (conventional, "pymatgen.get_conventional_standard_structure"),
        }
    except Exception:
        # 低对称、缺少周期晶胞或边界数值误差不能阻断已通过 ASE 的原始结构。
        return {
            "primitive": (atoms.copy(), "identity_fallback"),
            "conventional": (atoms.copy(), "identity_fallback"),
        }


def export_representations(
    atoms: Atoms,
) -> dict[CellKind, dict[StructureFormat, dict[str, Any]]]:
    representations: dict[CellKind, dict[StructureFormat, dict[str, Any]]] = {}
    for cell_kind, (cell_atoms, method) in standardize_cells(atoms).items():
        representations[cell_kind] = {}
        for structure_format in ("cif", "poscar"):
            text = serialize_atoms(cell_atoms, structure_format)
            representations[cell_kind][structure_format] = {
                "cell_kind": cell_kind,
                "format": structure_format,
                "text": text,
                "standardization_method": method,
                "validation": validate_atoms(cell_atoms, structure_format, source_text=text).as_dict(),
            }
    return representations


def structures_equivalent(left: Atoms, right: Atoms) -> bool:
    """按元素、晶胞和周期性坐标比较，而非比较 CIF/POSCAR 原始文本。"""
    try:
        from pymatgen.analysis.structure_matcher import StructureMatcher

        matcher = StructureMatcher(ltol=0.01, stol=0.1, angle_tol=5, primitive_cell=True)
        return bool(matcher.fit(_pymatgen_structure(left), _pymatgen_structure(right)))
    except Exception:
        return False


def build_structure_candidate(
    *,
    structure_format: str,
    structure_text: str,
    source: dict[str, Any],
    material_state_ref: str,
    source_kind: str = "attachment",
) -> dict[str, Any]:
    normalized = normalize_structure_format(structure_format)
    atoms = read_atoms(normalized, structure_text)
    validation = validate_atoms(atoms, normalized, source_text=structure_text).as_dict()
    return {
        "candidate_id": hashlib.sha256(
            f"{source.get('file_id') or source.get('filename') or ''}:{validation['structure_hash']}".encode()
        ).hexdigest()[:24],
        "material_state_ref": material_state_ref,
        "source_kind": source_kind,
        "status": "valid",
        "confirmation": "unreviewed",
        "original_format": normalized,
        "original_text": structure_text,
        "validation": validation,
        "derivation": None,
        "representations": export_representations(atoms),
        "sources": [dict(source)],
        "conflicts": [],
        "user_note": None,
    }
