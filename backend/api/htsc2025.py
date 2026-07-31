"""
HTSC-2025 常压高温超导体基准数据集 API
"""
import json
import os
from typing import List, Optional, Dict, Set
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/htsc2025", tags=["htsc2025"])

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data"
)
DATA_PATH = os.path.join(DATA_DIR, "htsc2025.json")

_dataset = None


def _load_dataset():
    global _dataset
    if _dataset is not None:
        return _dataset
    if not os.path.exists(DATA_PATH):
        raise RuntimeError("HTSC-2025 数据集未找到")

    with open(DATA_PATH) as f:
        data = json.load(f)
    _dataset = data
    return data


def _entry_matches(entry_elements: Set[str], query: Set[str], mode: str) -> bool:
    if not entry_elements:
        return False
    if mode == "only":
        return entry_elements == query
    elif mode == "combination":
        return entry_elements.issubset(query)
    elif mode == "contains":
        return query.issubset(entry_elements)
    return False


class HTSC2025SearchRequest(BaseModel):
    elements: List[str] = Field(..., description="元素符号列表")
    mode: str = Field("contains", description="筛选模式: only, combination, contains")
    min_tc: Optional[float] = Field(None, description="最低 Tc (K)")
    # 与前端筛选栏对齐的通用筛选参数
    tc_min: Optional[float] = Field(None, description="最低 Tc (K)，与 min_tc 等价且优先")
    tc_max: Optional[float] = Field(None, description="最高 Tc (K)")
    pressure_min: Optional[float] = Field(None, description="最低压强 (GPa)，数据集为常压（0 GPa）")
    pressure_max: Optional[float] = Field(None, description="最高压强 (GPa)")
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class HTSC2025SearchResult(BaseModel):
    items: List[dict]
    total: int
    has_prev: bool
    has_next: bool


@router.post("/search", response_model=HTSC2025SearchResult)
def search_htsc2025(request: HTSC2025SearchRequest):
    """按元素搜索 HTSC-2025 数据集中的材料"""
    if not request.elements:
        raise HTTPException(status_code=400, detail="至少需要选择一个元素")

    data = _load_dataset()
    records = data.get("records", [])
    query_set = set(request.elements)
    min_tc = request.tc_min if request.tc_min is not None else request.min_tc

    matched = []
    for r in records:
        entry_els = set(r.get("elements", []))
        if not _entry_matches(entry_els, query_set, request.mode):
            continue
        if min_tc is not None and r["tc"] < min_tc:
            continue
        if request.tc_max is not None and r["tc"] > request.tc_max:
            continue
        # 数据集均为常压材料，压强按 0 GPa 参与区间筛选
        if request.pressure_min is not None and request.pressure_min > 0:
            continue
        if request.pressure_max is not None and request.pressure_max < 0:
            continue
        matched.append(r)

    total = len(matched)
    page = matched[request.offset: request.offset + request.limit]

    return {
        "items": page,
        "total": total,
        "has_prev": request.offset > 0,
        "has_next": request.offset + request.limit < total,
    }


@router.get("/stats")
def htsc2025_stats():
    """返回 HTSC-2025 统计信息"""
    data = _load_dataset()
    records = data.get("records", [])
    classes = {}
    for r in records:
        cls = r.get("class", "unknown")
        if cls not in classes:
            classes[cls] = {"count": 0, "tcs": []}
        classes[cls]["count"] += 1
        classes[cls]["tcs"].append(r["tc"])

    stats = []
    for cls, info in sorted(classes.items()):
        tcs = info["tcs"]
        stats.append({
            "class": cls,
            "count": info["count"],
            "avg_tc": round(sum(tcs) / len(tcs), 1),
            "max_tc": max(tcs),
        })

    return {
        "total": len(records),
        "source": "https://github.com/xqh19970407/HTSC-2025",
        "classes": stats,
    }


@router.get("/detail/{name}")
def htsc2025_detail(name: str):
    """返回单个材料的详细数据（含 CIF）"""
    data = _load_dataset()
    name = name.replace("--", "-")
    raw = data.get("raw", {})
    if name in raw:
        rec = raw[name]
        rec["name"] = name
        return rec
    # 尝试模糊匹配
    for key in raw:
        if name in key or key.split("-")[-1] == name:
            rec = raw[key]
            rec["name"] = key
            return rec
    raise HTTPException(status_code=404, detail="材料未找到")
