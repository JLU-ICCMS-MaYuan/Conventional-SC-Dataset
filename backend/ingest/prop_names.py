"""
物性名称规范定义 — CSV 驱动

映射表：prop_name_map.csv (raw_pattern → canonical_name)
未命中时由 AI 决定映射并追加到 CSV，下次运行时自动生效。
"""

import csv
from pathlib import Path

_CSV_FILE = Path(__file__).resolve().parent / "prop_name_map.csv"

_CANONICAL_NAMES: list[str] = []
_PROP_LABELS: dict[str, str] = {}


def _load_map() -> list[tuple[str, str]]:
    """从 CSV 加载映射表 + 标签表。全局填充 _CANONICAL_NAMES 和 _PROP_LABELS。"""
    global _CANONICAL_NAMES, _PROP_LABELS
    if not _CSV_FILE.exists():
        return []
    rows = []
    labels = {}
    names = set()
    with open(_CSV_FILE, newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            r = [c.strip() for c in r]
            # 表头 / 注释 / 空行跳过
            if not r or not r[0] or r[0].startswith("#") or r[0] == "raw_pattern":
                continue
            # 映射行: raw_pattern, canonical_name[, label]
            if len(r) >= 2 and r[0] and r[1]:
                rows.append((r[0].lower(), r[1]))
                names.add(r[1])
                if len(r) >= 3 and r[2]:
                    labels[r[1]] = r[2]
    _PROP_LABELS = labels
    _CANONICAL_NAMES = sorted(names)
    return rows

# 首次加载
_load_map()

# 兼容旧代码的 PROP_LABELS 引用
PROP_LABELS = _PROP_LABELS


def _append_to_csv(raw: str, canonical: str) -> None:
    """追加新映射到 CSV 文件末尾。"""
    already = False
    if _CSV_FILE.exists():
        existing = _CSV_FILE.read_text()
        already = f"{raw},{canonical}" in existing or f'"{raw}","{canonical}"' in existing
    if not already:
        with open(_CSV_FILE, "a", newline="", encoding="utf-8") as f:
            import csv as _csv
            w = _csv.writer(f)
            w.writerow([raw.strip(), canonical])


def normalize_prop_name(raw: str | None) -> tuple[str, bool]:
    """CSV 驱动的物性名归一化。子串匹配，命中第一个返回。

    Returns:
        (规范名, True)  —— CSV 中命中
        (原名, False)   —— 未命中
    """
    s = (raw or "").strip()
    if not s:
        return s, True
    low = s.lower()
    for pattern, canonical in _load_map():
        if pattern in low:
            return canonical, True
    return s, False


def ai_normalize(raw_name: str) -> str:
    """用 AI 将未命中的原始物性名映射到规范名，结果写入 CSV。"""
    key = raw_name.strip()
    if not key:
        return key

    # 先检查 CSV（可能其他进程已添加）
    canonical, matched = normalize_prop_name(key)
    if matched:
        return canonical

    try:
        from backend.ingest.enrich_papers import deepseek_chat
        options = "\n".join(f"- {n}: {PROP_LABELS.get(n, n)}" for n in _CANONICAL_NAMES)
        prompt = f"""将以下物性名映射到最接近的规范名。只输出规范名，不要解释。

原始名: {key}

可选规范名:
{options}

如果都不匹配，输出原始名本身。

规范名:"""
        result = deepseek_chat([{"role": "user", "content": prompt}], None).strip()
        result = result.split("\n")[0].strip().rstrip(".")
        if result not in _CANONICAL_NAMES:
            result = key
    except Exception:
        result = key

    _append_to_csv(key, result)
    return result
