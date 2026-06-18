"""
extractor.py — LLM 结构化提取模块。

将 Markdown 论文文本发给 DeepSeek（OpenAI 兼容接口），
返回结构化的论文元信息 + 超导数据点列表。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


SYSTEM_PROMPT = """你是一个材料科学专家，专门研究超导材料。从论文文本中提取结构化数据，严格按照以下 JSON 格式返回。

## 必须返回的 JSON 结构

{
  "title": "论文标题（从 # 标题行或正文开头提取）",
  "doi": "DOI 号，如 10.1103/PhysRevLett.126.117002，找不到则 null",
  "authors": ["第一作者", "第二作者"],
  "journal": "期刊全称，如 Physical Review Letters、Nature Communications，找不到则 null",
  "year": 2024,
  "abstract": "摘要全文，找不到则 null",
  "paper_type": "theoretical / experimental / review / unknown",
  "summary": "中文总结，100-200字，包含研究对象、计算方法/实验手段、主要结果（最高 Tc 数值）、结论",
  "keywords_tags": ["超导", "LaH10", "高压", ...],
  "data_points": [
    {
      "article_type": "t",
      "superconductor_type": "h",
      "chemical_formula": "LaH10  或 H 或 H3S",
      "pressure_gpa": 200.0,
      "space_group_symbol": "Fm-3m",
      "crystal_structure": "cubic",
      "thermodynamically_stable": true,
      "dynamically_stable": true,
      "energy_above_hull": 12.5,
      "mcmillan_tc": [240, 245],
      "allen_dynes_tc": [250, 255],
      "experimental_tc": 260.0,
      "lambda_value": 2.5,
      "omega_log": 1200.0,
      "n_ef_total": 2.0,
      "element_n_ef": {"La": 0.2, "H": 1.8},
      "pseudopotential_type": "PAW",
      "exchange_correlation": "PBE",
      "calculation_code": "Quantum ESPRESSO",
      "k_grid": "16x16x16",
      "q_grid": "4x4x4",
      "energy_cutoff": 80,
      "energy_cutoff_unit": "Ry",
      "method": "Allen-Dynes formula",
      "data_source_note": "从 Table 1 提取"
    }
  ]
}

## 字段提取要点

### 论文元信息
- title: 从文件开头的 # 标题或正文第一段提取
- doi: 全文搜索 "doi: 10." 或 "10.10" 或 "https://doi.org/" 模式
- authors: 从标题下方作者行提取，存为字符串数组，不要带序号标记
- journal: 按优先级从以下线索提取：(1) 文中 "Peer review information [期刊名]" 行 (2) DOI 域名（10.1103/→Phys.Rev.、10.1038/→Nature、10.1063/→AIP、10.1073/→PNAS）(3) 文中 "Published in" / "Published by" / "Published online" 附近文字 (4) 参考文献列表中与当前论文标题相似的那条
- year: 从 "Received/Accepted/Published" 日期、或 "year" 字段、或文件夹/文件名中的年份提取
- abstract: 从 "Abstract" 或 "摘要" 后面提取完整段落

### data_points 提取规则
- 表格中的**每一行数据**都要单独提取为一个 data_point
- 同一化合物在不同压力下拆成多个 data_point
- **提取的data应当为本文主要研究目标**（包括标题里的 Tc 和摘要里的 Tc）
- 理论计算值（mcmillan_tc/allen_dynes_tc）和实验测量值（experimental_tc）分开放入不同字段
- 固体氢/金属氢的论文：化学式填 "H"，提取压力和 Tc
- energy_above_hull 单位为 meV/atom，没有则 null
- 只提取论文自己报道的结果，不提取引用其他文献的数据
- 如果 Tc 给出的是范围（如 34-35 K），取平均值（34.5 K）
- 如果明确写了 "Tc ≈ X K"、"Tc = X K"、"X K" 字样，提取数值
- 如果论文提到了赝势类型（PAW/USPP/NCPP）、交换关联泛函（PBE/PBEsol/LDA）、计算软件（VASP/Quantum ESPRESSO/CASTEP）、k 点网格、截断能等计算设置信息，一并提取
- method 字段描述 Tc 的计算方法，如 "McMillan formula"、"Allen-Dynes"、"Eliashberg equation"
- thermodynamically_stable / dynamically_stable: 布尔值，描述是否热力学/动力学稳定
- element_n_ef: 各元素对费米面态密度的贡献 JSON，如 {"La": 0.2, "H": 1.8}
- article_type: 每条数据标"e"(实验)或"t"(理论)，无法判断则 null
- superconductor_type: 按主要研究对象分类，"h"(氢化物)/"c"(铜氧化物)/"i"(铁基)/"n"(镍基)/"cb"(碳基)/"or"(有机)/"ot"(其他)，无法判断则 null
- data_source_note: 数据来源备注，如 "estimated from BCS"、"from Figure 3(d)"、"范围值取平均"
- tc 字段（mcmillan_tc/allen_dynes_tc/experimental_tc）：单值用数字，范围用数组 [min, max]"""


def _openai_client() -> OpenAI:
    """创建 OpenAI 兼容客户端（用于 DeepSeek）。"""
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )


@dataclass
class ExtractionResult:
    """一篇论文的完整提取结果。"""
    paper: dict[str, Any] = field(default_factory=dict)
    data_points: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    keywords_tags: list[str] = field(default_factory=list)
    paper_type: str = "unknown"
    raw_json: dict[str, Any] | None = None  # LLM 返回的原始 JSON


def extract_from_markdown(markdown_text: str, model: str | None = None) -> ExtractionResult:
    """调 DeepSeek 从 Markdown 中提取结构化数据。

    Args:
        markdown_text: 论文的 Markdown 文本
        model: 模型名，默认使用 settings.deepseek_model

    Returns:
        ExtractionResult 对象
    """
    model_name = model or settings.deepseek_model
    client = _openai_client()

    # 截断：DeepSeek 模型上下文 64K，留足输出空间
    max_input_chars = 18000
    truncated = markdown_text[:max_input_chars]

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": truncated},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,  # 低温度保证输出稳定
    )

    usage = resp.usage
    if usage is not None:
        print(
            f"    Tokens — prompt: {usage.prompt_tokens}, "
            f"completion: {usage.completion_tokens}, "
            f"cache hit: {usage.prompt_cache_hit_tokens}, "
            f"cache miss: {usage.prompt_cache_miss_tokens}"
        )

    raw = json.loads(resp.choices[0].message.content)
    return _parse_result(raw)


def _parse_result(raw: dict[str, Any]) -> ExtractionResult:
    """解析 LLM 返回的 JSON 为 ExtractionResult。

    兼容两种格式：
    格式 A: {"paper": {...}, "data_points": [...]}
    格式 B: {"title": "...", "doi": "...", "data_points": [...]} （无 paper 包装）
    """
    # ── 兼容两种 JSON 结构 ────────────────────────────────────────────
    paper_data = raw.get("paper") or {}
    # 如果没有 "paper" 层，直接从顶层读取
    if not paper_data and ("title" in raw or "doi" in raw):
        paper_data = raw

    data_points_raw = raw.get("data_points") or raw.get("data") or []

    # ── 处理 authors：可能是字符串或数组 ────────────────────────────────
    authors_raw = paper_data.get("authors")
    if isinstance(authors_raw, list):
        authors_str = "; ".join(str(a) for a in authors_raw if a)
    else:
        authors_str = _safe_str(authors_raw)

    # ── 处理 year：可能是数字或从 publication_date 提取 ──────────────────
    year = _safe_int(paper_data.get("year"))
    if year is None and paper_data.get("publication_date"):
        date_str = str(paper_data.get("publication_date", ""))
        import re
        m = re.search(r"(19\d{2}|20\d{2})", date_str)
        if m:
            year = int(m.group(1))

    # ── 处理 summary 和 keywords_tags ───────────────────────────────────
    summary = raw.get("summary") or paper_data.get("summary") or ""
    keywords_tags = raw.get("keywords_tags") or paper_data.get("keywords_tags") or []

    def _resolve_tc(v):
        """Tc 可能是单值或数组 [min, max]，统一为 float（数组取平均）。"""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, list) and len(v) > 0:
            vals = [x for x in v if x is not None]
            if not vals:
                return None
            return sum(float(x) for x in vals) / len(vals)
        if isinstance(v, str):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        return None

    def _resolve_bool(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "yes", "1")
        return None

    # ── 标准化 data_points ──────────────────────────────────────────────
    data_points = []
    for dp in data_points_raw:
        if not isinstance(dp, dict):
            continue

        cleaned = {
            "article_type": _safe_str(dp.get("article_type")),
            "superconductor_type": _safe_str(dp.get("superconductor_type")),
            "chemical_formula": _safe_str(dp.get("chemical_formula")),
            "pressure_gpa": _safe_float(dp.get("pressure_gpa")),
            "space_group_symbol": _safe_str(dp.get("space_group_symbol")),
            "crystal_structure": _safe_str(dp.get("crystal_structure")),
            "thermodynamically_stable": _resolve_bool(dp.get("thermodynamically_stable")),
            "dynamically_stable": _resolve_bool(dp.get("dynamically_stable")),
            "energy_above_hull": _safe_float(dp.get("energy_above_hull")),
            "tc_k": _resolve_tc(dp.get("tc_k")),
            "mcmillan_tc": _resolve_tc(dp.get("mcmillan_tc")),
            "allen_dynes_tc": _resolve_tc(dp.get("allen_dynes_tc")),
            "experimental_tc": _resolve_tc(dp.get("experimental_tc")),
            "lambda_value": _safe_float(dp.get("lambda_value")),
            "omega_log": _safe_float(dp.get("omega_log")),
            "n_ef_total": _safe_float(dp.get("n_ef_total")),
            "element_n_ef": dp.get("element_n_ef"),
            "pseudopotential_type": _safe_str(dp.get("pseudopotential_type")),
            "exchange_correlation": _safe_str(dp.get("exchange_correlation")),
            "calculation_code": _safe_str(dp.get("calculation_code")),
            "k_grid": _safe_str(dp.get("k_grid")),
            "q_grid": _safe_str(dp.get("q_grid")),
            "energy_cutoff": _safe_float(dp.get("energy_cutoff")),
            "energy_cutoff_unit": _safe_str(dp.get("energy_cutoff_unit")),
            "method": _safe_str(dp.get("method")),
            "data_source_note": _safe_str(dp.get("data_source_note")),
            "source_label": "paper",
        }
        # 跳过完全没有数据的空行
        has_data = any(
            cleaned[k] is not None
            for k in ("chemical_formula", "pressure_gpa", "lambda_value",
                      "mcmillan_tc", "allen_dynes_tc", "experimental_tc", "tc_k")
        )
        if has_data:
            data_points.append(cleaned)

    paper = {
        "doi": _safe_str(paper_data.get("doi")),
        "title": _safe_str(paper_data.get("title")),
        "authors": authors_str,
        "journal": _safe_str(paper_data.get("journal")),
        "year": year,
        "abstract": _safe_str(paper_data.get("abstract")),
        "paper_type": _safe_str(raw.get("paper_type") or paper_data.get("paper_type")) or "unknown",
    }

    result = ExtractionResult(
        paper=paper,
        data_points=data_points,
        summary=summary,
        keywords_tags=keywords_tags if isinstance(keywords_tags, list) else [],
        paper_type=paper.get("paper_type") or "unknown",
        raw_json=raw,
    )
    return result


def _safe_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None
