"""
storer.py — 数据库写入模块。

将提取结果写入数据库，处理判重和关联逻辑：
Paper → ChemicalSystem → Superconductor → SuperconductorRecord
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.rag.models import (
    ChemicalSystem,
    Paper,
    Superconductor,
    SuperconductorRecord,
)
from backend.rag.ingest.extractor import ExtractionResult


def _parse_formula(formula: str) -> dict[str, int]:
    """解析化学式，返回 {元素符号: 原子数}。"""
    result: dict[str, int] = {}
    # 匹配元素符号 + 可选数字，如 LaH10 → {La: 1, H: 10}
    for match in re.finditer(r"([A-Z][a-z]?)(\d*)", formula):
        symbol = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        result[symbol] = result.get(symbol, 0) + count
    return result


def _sort_elements(elements: dict[str, int]) -> tuple[list[str], list[str], str]:
    """将元素按字母排序，返回 (sorted_symbols, sorted_elements_with_counts, system_key)。"""
    sorted_symbols = sorted(elements.keys())
    system_key = "-".join(sorted_symbols)
    return sorted_symbols, system_key


def _normalize_formula(elements: dict[str, int]) -> str:
    """生成归一化化学式（元素符号字母排序）：LaH10 → H10La。"""
    sorted_symbols = sorted(elements.keys())
    parts = []
    for sym in sorted_symbols:
        count = elements[sym]
        parts.append(f"{sym}{count}" if count > 1 else sym)
    return "".join(parts)


def _compute_ratio(elements: dict[str, int]) -> dict[str, float]:
    """计算元素比例。"""
    total = sum(elements.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in elements.items()}


async def store_extraction(
    session: AsyncSession,
    result: ExtractionResult,
    source_file_path: str,
) -> int:
    """将提取结果写入数据库。

    Args:
        session: SQLAlchemy async session
        result: 提取结果
        source_file_path: mineru 中的相对路径

    Returns:
        paper_id
    """
    paper_data = result.paper

    # ── 1. Paper ────────────────────────────────────────────────────────
    # 查重：先按 DOI 查，再按 source_file_path 查
    existing_paper = None
    doi = paper_data.get("doi")
    if doi:
        r = await session.execute(select(Paper).where(Paper.doi == doi))
        existing_paper = r.scalar_one_or_none()

    if not existing_paper:
        r = await session.execute(
            select(Paper).where(Paper.source_file_path == source_file_path)
        )
        existing_paper = r.scalar_one_or_none()

    if existing_paper:
        paper_id = existing_paper.id
        # 更新现有记录
        for key, val in paper_data.items():
            if val is not None:
                setattr(existing_paper, key, val)
        existing_paper.summary = result.summary or existing_paper.summary
        existing_paper.keywords_tags = json.dumps(result.keywords_tags, ensure_ascii=False) if result.keywords_tags else existing_paper.keywords_tags
        existing_paper.source_file_path = source_file_path
        existing_paper.paper_type = result.paper_type or existing_paper.paper_type
        print(f"  [存储] 更新已有 Paper id={paper_id}")
    else:
        import re
        paper = Paper(
            doi=doi,
            review_status="pending" if re.match(r"^upload/", source_file_path) else "approved",
            title=paper_data.get("title"),
            authors=paper_data.get("authors"),
            journal=paper_data.get("journal"),
            year=paper_data.get("year"),
            abstract=paper_data.get("abstract"),
            summary=result.summary,
            keywords_tags=json.dumps(result.keywords_tags, ensure_ascii=False) if result.keywords_tags else None,
            source_file_path=source_file_path,
            paper_type=result.paper_type,
        )
        session.add(paper)
        await session.flush()
        paper_id = paper.id
        print(f"  [存储] 新建 Paper id={paper_id}")

    # ── 2. Data Points → ChemicalSystem → Superconductor → Record ──────
    for dp in result.data_points:
        formula = dp.get("chemical_formula")
        if not formula:
            continue

        # 解析化学式
        elements = _parse_formula(formula)
        if not elements:
            continue

        _, system_key = _sort_elements(elements)
        formula_normalized = _normalize_formula(elements)
        elements_list = json.dumps(sorted(elements.keys()), ensure_ascii=False)
        composition = json.dumps(elements, ensure_ascii=False)
        ratio = _compute_ratio(elements)
        element_ratio = json.dumps(ratio, ensure_ascii=False)

        # ── ChemicalSystem ──────────────────────────────────────────────
        r = await session.execute(
            select(ChemicalSystem).where(ChemicalSystem.system_key == system_key)
        )
        chem_sys = r.scalar_one_or_none()
        if not chem_sys:
            chem_sys = ChemicalSystem(
                system_key=system_key,
                elements_list=elements_list,
                element_count=len(elements),
            )
            session.add(chem_sys)
            await session.flush()

        # ── Superconductor ──────────────────────────────────────────────
        r = await session.execute(
            select(Superconductor).where(
                Superconductor.chemical_system_id == chem_sys.id,
                Superconductor.formula_normalized == formula_normalized,
            )
        )
        sc = r.scalar_one_or_none()
        if not sc:
            sc = Superconductor(
                chemical_system_id=chem_sys.id,
                chemical_formula=formula,
                formula_normalized=formula_normalized,
                elements_list=elements_list,
                composition=composition,
                element_ratio=element_ratio,
            )
            session.add(sc)
            await session.flush()

        # ── SuperconductorRecord ────────────────────────────────────────
        # 兼容 tc_k 旧字段和 mcmillan/allen_dynes/experimental 新字段
        tc_k = dp.get("tc_k")
        mcmillan_tc = dp.get("mcmillan_tc") or (tc_k if not dp.get("allen_dynes_tc") else None)
        allen_dynes_tc = dp.get("allen_dynes_tc") or tc_k
        experimental_tc = dp.get("experimental_tc")

        record = SuperconductorRecord(
            superconductor_id=sc.id,
            paper_id=paper_id,
            source_label=dp.get("source_label", "paper"),
            article_type=dp.get("article_type"),
            superconductor_type=dp.get("superconductor_type"),
            pressure_gpa=dp.get("pressure_gpa"),
            space_group_symbol=dp.get("space_group_symbol"),
            crystal_structure=dp.get("crystal_structure"),
            thermodynamically_stable=dp.get("thermodynamically_stable"),
            dynamically_stable=dp.get("dynamically_stable"),
            energy_above_hull=dp.get("energy_above_hull"),
            mcmillan_tc=mcmillan_tc,
            allen_dynes_tc=allen_dynes_tc,
            experimental_tc=experimental_tc,
            lambda_value=dp.get("lambda_value"),
            omega_log=dp.get("omega_log"),
            n_ef_total=dp.get("n_ef_total"),
            element_n_ef=json.dumps(dp.get("element_n_ef"), ensure_ascii=False) if isinstance(dp.get("element_n_ef"), dict) else None,
            pseudopotential_type=dp.get("pseudopotential_type"),
            exchange_correlation_functional=dp.get("exchange_correlation"),
            calculation_code=dp.get("calculation_code"),
            k_grid=dp.get("k_grid"),
            q_grid=dp.get("q_grid"),
            energy_cutoff_value=dp.get("energy_cutoff"),
            energy_cutoff_unit=dp.get("energy_cutoff_unit"),
            method=dp.get("method"),
            data_source_note=dp.get("data_source_note"),
            show_in_chart=False,
        )
        session.add(record)

    await session.commit()
    print(f"  [存储] 写入 {len(result.data_points)} 个数据点")
    return paper_id
