"""
extractor.py — LLM 结构化提取模块（v2 精简版）。

将 Markdown 论文文本发给 DeepSeek，返回论文元信息（title/summary/keywords/paper_type）。
物性表 key_properties 由 enrich_papers 管线负责，extractor 不再提取 data_points。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


SYSTEM_PROMPT = """你是一个材料科学专家，专门研究超导材料。从论文文本中提取结构化元信息，严格按照以下 JSON 格式返回。

## 必须返回的 JSON 结构

{
  "title": "论文标题（从 # 标题行或正文开头提取）",
  "doi": "DOI 号，如 10.1103/PhysRevLett.126.117002，找不到则 null",
  "authors": ["第一作者", "第二作者"],
  "corresponding_authors": ["通讯作者"],
  "co_first_authors": ["共同第一作者1", "共同第一作者2"],
  "journal": "期刊全称，如 Physical Review Letters、Nature Communications，找不到则 null",
  "year": 2024,
  "abstract": "摘要全文，找不到则 null",
  "paper_type": "theoretical / experimental / review / unknown",
  "summary": "中文总结，100-200字，包含研究对象、计算方法/实验手段、主要结果（最高 Tc 数值)、结论",
  "keywords_tags": ["超导", "LaH10", "高压", ...]
}

## 字段提取要点

- title: 从文件开头的 # 标题或正文第一段提取
- doi: 全文搜索 "doi: 10." 或 "10.10" 或 "https://doi.org/" 模式
- authors: 从标题下方作者行提取，存为字符串数组，不要把序号、星号或脚注符号写入姓名
- corresponding_authors: 仅根据星号说明、通讯邮箱或 correspondence 声明识别；证据不足时返回空数组
- co_first_authors: 仅根据 equal contribution、contributed equally 等明确声明识别；证据不足时返回空数组
- journal: 按优先级从以下线索提取：(1) 文中 "Peer review information [期刊名]" 行 (2) DOI 域名（10.1103/→Phys.Rev.、10.1038/→Nature、10.1063/→AIP、10.1073/→PNAS）(3) 文中 "Published in" / "Published by" / "Published online" 附近文字 (4) 参考文献列表中与当前论文标题相似的那条
- year: 从 "Received/Accepted/Published" 日期、或 "year" 字段、或文件夹/文件名中的年份提取
- abstract: 从 "Abstract" 或 "摘要" 后面提取完整段落
- paper_type: 判定论文类型。theoretical=纯理论/计算，experimental=有实验合成/测量数据，review=综述，unknown=无法判断
- summary: 中文总结 100-200 字，包含研究体系、核心方法与手段、最高 Tc 与对应的压力条件、主要突破
- keywords_tags: 5-10 个中文关键词，包含材料名、方法名、关键物性类别"""


def _openai_client() -> OpenAI:
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )


@dataclass
class ExtractionResult:
    """一篇论文的完整提取结果。"""
    paper: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    keywords_tags: list[str] = field(default_factory=list)
    paper_type: str = "unknown"
    raw_json: dict[str, Any] | None = None


def extract_from_markdown(markdown_text: str, model: str | None = None) -> ExtractionResult:
    """调 DeepSeek 从 Markdown 中提取论文元信息。"""
    model_name = model or settings.deepseek_model
    client = _openai_client()

    # 分类必须基于全文；不再固定截断输入。
    truncated = markdown_text

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": truncated},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    usage = resp.usage
    if usage is not None:
        # 不同 OpenAI/兼容 API 的 CompletionUsage 字段不完全一致。
        # 缓存 token 字段缺失时不能阻断论文解析。
        prompt_tokens = getattr(usage, "prompt_tokens", "?")
        completion_tokens = getattr(usage, "completion_tokens", "?")
        cache_hit = getattr(usage, "prompt_cache_hit_tokens", "?")
        cache_miss = getattr(usage, "prompt_cache_miss_tokens", "?")
        print(
            f"    Tokens — prompt: {prompt_tokens}, "
            f"completion: {completion_tokens}, cache hit: {cache_hit}, cache miss: {cache_miss}"
        )

    raw = json.loads(resp.choices[0].message.content)
    return _parse_result(raw)


def _parse_result(raw: dict[str, Any]) -> ExtractionResult:
    """解析 LLM 返回的 JSON 为 ExtractionResult。

    兼容两种格式：
    格式 A: {"paper": {...}, ...}
    格式 B: {"title": "...", "doi": "...", ...} （无 paper 包装）
    """
    paper_data = raw.get("paper") or {}
    if not paper_data and ("title" in raw or "doi" in raw):
        paper_data = raw

    # authors：可能是字符串或数组
    authors_raw = paper_data.get("authors")
    if isinstance(authors_raw, list):
        authors_str = "; ".join(str(a) for a in authors_raw if a)
    else:
        authors_str = _safe_str(authors_raw)

    # year：可能是数字或从 publication_date 提取
    year = _safe_int(paper_data.get("year"))
    if year is None and paper_data.get("publication_date"):
        m = re.search(r"(19\d{2}|20\d{2})", str(paper_data.get("publication_date", "")))
        if m:
            year = int(m.group(1))

    summary = raw.get("summary") or paper_data.get("summary") or ""
    keywords_tags = raw.get("keywords_tags") or paper_data.get("keywords_tags") or []

    paper = {
        "doi": _safe_str(paper_data.get("doi")),
        "title": _safe_str(paper_data.get("title")),
        "authors": authors_str,
        "corresponding_authors": paper_data.get("corresponding_authors") or [],
        "co_first_authors": paper_data.get("co_first_authors") or [],
        "journal": _safe_str(paper_data.get("journal")),
        "year": year,
        "abstract": _safe_str(paper_data.get("abstract")),
        "paper_type": _safe_str(raw.get("paper_type") or paper_data.get("paper_type")) or "unknown",
    }

    return ExtractionResult(
        paper=paper,
        summary=summary,
        keywords_tags=keywords_tags if isinstance(keywords_tags, list) else [],
        paper_type=paper.get("paper_type") or "unknown",
        raw_json=raw,
    )


def _safe_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None
