"""
超导类型规范定义（单一事实源）

规范全称（与 schemas.PaperCreate.superconductor_type 一致）：
    hydride / cuprate / iron_based / nickel_based / carbon / organic / others
历史缩写码（摄入管线 LLM 输出，语义以 ingest/data/extractor.py 为准）：
    h=氢化物, c=铜氧化物, i=铁基, n=镍基, cb=碳基, or=有机, ot=其他
"""

# 规范全称 → 中文标签
SC_TYPE_LABELS = {
    "hydride": "高压氢化物",
    "cuprate": "铜氧化物",
    "iron_based": "铁基",
    "nickel_based": "镍基",
    "carbon": "碳基",
    "organic": "有机",
    "others": "其他超导",
}

# 各类历史写法 → 规范全称
SC_TYPE_ALIASES = {
    # 摄入管线历史缩写码
    "h": "hydride", "c": "cuprate", "i": "iron_based", "n": "nickel_based",
    "cb": "carbon", "or": "organic", "ot": "others",
    # 规范全称自映射
    **{name: name for name in SC_TYPE_LABELS},
    # 其他历史别名（原 schemas legacy_map 与常见变体）
    "hydrides": "hydride",
    "iron-based": "iron_based",
    "nickel-based": "nickel_based",
    "carbon_organic": "carbon",
    "conventional": "others",
    "other_conventional": "others",
    "unconventional": "others",
    "other_unconventional": "others",
    "unknown": "others",
    "other": "others",
}


def normalize_sc_type(value: str | None) -> str | None:
    """归一化超导类型为规范全称；空值/All/无法识别时返回 None"""
    key = (value or "").strip().lower()
    if not key or key == "all":
        return None
    return SC_TYPE_ALIASES.get(key)
