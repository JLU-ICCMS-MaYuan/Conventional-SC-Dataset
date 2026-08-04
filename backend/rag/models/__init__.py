# 统一从 backend.models 导出所有模型（双 ORM 已合并）
from backend.models import (
    ChemicalSystem,
    KeyProperty,
    Paper,
    PaperChunk,
    PeriodicTableElement,
    Superconductor,
    SuperconductorRecord,
    User,
)

__all__ = [
    "ChemicalSystem",
    "KeyProperty",
    "Paper",
    "PaperChunk",
    "PeriodicTableElement",
    "Superconductor",
    "SuperconductorRecord",
    "User",
]
