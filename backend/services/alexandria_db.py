"""
Alexandria 电声耦合数据库查询模块
从预索引 JSON 文件中快速检索材料数据
"""
import json
import os
import time
from typing import List, Optional, Dict, Any

ALEXANDRIA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "alexandria"
)
INDEX_FILE = os.path.join(ALEXANDRIA_DIR, "_index.json")

_index: List[Dict[str, Any]] = None
_index_loaded = False


def _build_index() -> List[Dict[str, Any]]:
    """扫描所有 JSON 文件，提取关键字段构建索引"""
    files = sorted([
        f for f in os.listdir(ALEXANDRIA_DIR)
        if f.startswith("alexandria_ph_") and f.endswith(".json")
    ])
    if not files:
        print("未找到 Alexandria 数据文件")
        return []

    entries = []
    t0 = time.time()
    for i, filename in enumerate(files):
        filepath = os.path.join(ALEXANDRIA_DIR, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
        except Exception as e:
            print(f"读取 {filename} 失败: {e}")
            continue

        for raw in data.get("entries", []):
            d = raw.get("data", {})
            tc_data = d.get("tc")
            tc_summary = None
            if tc_data and isinstance(tc_data, dict):
                tc_mcm = tc_data.get("TcMcMillan")
                tc_ad = tc_data.get("TcAllenDynes")
                tc_max = 0.0
                if tc_mcm and isinstance(tc_mcm, list):
                    vals = [v for v in tc_mcm if v is not None]
                    if vals:
                        tc_max = max(max(vals), tc_max)
                if tc_ad and isinstance(tc_ad, list):
                    vals = [v for v in tc_ad if v is not None]
                    if vals:
                        tc_max = max(max(vals), tc_max)
                tc_summary = {
                    "lambda": tc_data.get("lambda"),
                    "wlog": tc_data.get("wlog[K]"),
                    "tc_max": round(tc_max, 2),
                    "mustr": tc_data.get("mustr"),
                    "TcMcMillan": tc_mcm,
                    "TcAllenDynes": tc_ad,
                }

            entry = {
                "mat_id": d.get("mat_id"),
                "formula": d.get("formula"),
                "elements": d.get("elements", []),
                "spg": d.get("spg"),
                "nsites": d.get("nsites"),
                "tc": tc_summary,
                "imag": d.get("imag", True),
                "band_gap": d.get("band_gap_ind"),
                "dos_ef": d.get("dos_ef"),
                "e_above_hull": d.get("e_above_hull"),
                "e_form": d.get("e_form"),
                "energy_total": d.get("energy_total"),
            }
            entries.append(entry)

        if (i + 1) % 10 == 0:
            print(f"  索引进度: {i+1}/{len(files)} 文件, {len(entries)} 条")

    print(f"索引构建完成: {len(entries)} 条, 耗时 {time.time()-t0:.1f}s")

    # 保存索引文件供后续快速加载
    try:
        with open(INDEX_FILE, "w") as f:
            json.dump(entries, f, ensure_ascii=False)
        print(f"索引已保存至 {INDEX_FILE}")
    except Exception as e:
        print(f"保存索引文件失败: {e}")

    return entries


def _load_index() -> List[Dict[str, Any]]:
    """加载索引（优先读取预构建的索引文件）"""
    global _index, _index_loaded

    if _index_loaded:
        return _index

    t0 = time.time()
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE) as f:
                _index = json.load(f)
            print(f"加载索引: {len(_index)} 条, 耗时 {time.time()-t0:.1f}s")
            _index_loaded = True
            return _index
        except Exception as e:
            print(f"读取索引文件失败，将重新构建: {e}")

    _index = _build_index()
    _index_loaded = True
    return _index


def _entry_matches_elements(entry: Dict, selection: set, mode: str) -> bool:
    """检查条目是否匹配元素筛选条件"""
    entry_elements = set(entry.get("elements", []))
    if not entry_elements:
        return False

    if mode == "only":
        return entry_elements == selection
    elif mode == "combination":
        return entry_elements.issubset(selection)
    elif mode == "contains":
        return selection.issubset(entry_elements)
    return False


def search_by_elements(
    elements: List[str],
    mode: str = "contains",
    min_tc: Optional[float] = None,
    stable_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> Dict:
    """
    按元素搜索 Alexandria 数据库

    Args:
        elements: 元素符号列表
        mode: only/combination/contains
        min_tc: 最低 Tc 筛选
        stable_only: 仅显示动力学稳定（无虚声子）的条目
        limit: 每页数量
        offset: 偏移量

    Returns:
        {"items": [...], "total": int, "has_prev": bool, "has_next": bool}
    """
    entries = _load_index()
    selection = set(elements)

    if not selection:
        return {"items": [], "total": 0, "has_prev": False, "has_next": False}

    matched = []
    for entry in entries:
        if not _entry_matches_elements(entry, selection, mode):
            continue
        if stable_only and entry.get("imag", True):
            continue
        tc = entry.get("tc")
        if min_tc is not None:
            if not tc or tc.get("tc_max", 0) < min_tc:
                continue

        matched.append(entry)

    total = len(matched)
    page_items = matched[offset: offset + limit]

    return {
        "items": page_items,
        "total": total,
        "has_prev": offset > 0,
        "has_next": offset + limit < total,
    }


def clear_cache():
    """清空内存缓存，下次查询时重新加载"""
    global _index, _index_loaded
    _index = None
    _index_loaded = False
