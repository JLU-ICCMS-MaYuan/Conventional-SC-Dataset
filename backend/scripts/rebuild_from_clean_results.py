"""物性清洗阶段使用的纯函数。"""

from __future__ import annotations

import re
from collections import defaultdict
from numbers import Real
from typing import Any


def parse_formula(formula: str) -> dict[str, float]:
    """将简单化学式解析为元素计数。"""
    result: dict[str, float] = defaultdict(float)
    for element, count in re.findall(r"([A-Z][a-z]?)(\d*(?:\.\d+)?)", formula or ""):
        result[element] += float(count or 1)
    return dict(result)


def normalize_formula(elements: dict[str, float]) -> str:
    return "".join(f"{k}{v:g}" if v != 1 else k for k, v in sorted(elements.items()))


def parse_range(value: Any) -> tuple[float | None, float | None, str | None]:
    raw = str(value).strip() if value is not None else ""
    nums = re.findall(r"\d+(?:\.\d+)?", raw)
    if not nums:
        return None, None, raw or None
    values = [float(n) for n in nums]
    return min(values), max(values), raw


def extract_cond_number(condition: Any, key: str) -> float | None:
    if not isinstance(condition, dict):
        return None
    value = condition.get(key)
    if isinstance(value, Real):
        return float(value)
    values = re.findall(r"[-+]?\d+(?:\.\d+)?", str(value or ""))
    return float(values[0]) if values else None



def paper_is_experimental(paper_type: Any) -> bool:
    labels = paper_type if isinstance(paper_type, (list, tuple, set)) else [paper_type]
    normalized = {str(label or "").strip().lower() for label in labels}
    return bool(normalized & {"experimental", "experiment", "e"})


def infer_sc_type(elements: dict[str, float] | str | None, pressure: float | None = None) -> str:
    if isinstance(elements, str):
        elements = parse_formula(elements)
    symbols = {str(symbol).capitalize() for symbol in (elements or {})}
    if "H" in symbols and len(symbols) <= 3: return "hydride"
    if "Cu" in symbols: return "cuprate"
    if "Fe" in symbols: return "iron_based"
    if "Ni" in symbols: return "nickel_based"
    if symbols <= {"C"} or ("C" in symbols and len(symbols) <= 3): return "carbon"
    return "others"
