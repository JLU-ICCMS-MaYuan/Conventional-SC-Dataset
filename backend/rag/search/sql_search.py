"""
sql_search.py — SQL 精确搜索模块。

支持 4 种搜索模式（按 example.md 设计）：
1. formula_search: 精确搜索化学式（LaH10）
2. elements_exact_search: 精确元素体系（La-H 只返回 H-La）
3. elements_combination_search: 元素子集组合
4. elements_contained_search: 包含搜索
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.rag.models import (
    ChemicalSystem,
    Paper,
    Superconductor,
    SuperconductorRecord,
)


async def search_by_formula(
    session: AsyncSession,
    formula: str,
) -> list[dict]:
    """按化学式精确搜索超导体。

    返回该超导体的所有数据记录（含 paper 信息）。
    """
    from sqlalchemy.orm import joinedload

    # 先找 superconductor
    r = await session.execute(
        select(Superconductor)
        .where(Superconductor.chemical_formula.ilike(formula))
        .options(joinedload(Superconductor.records).joinedload(SuperconductorRecord.paper))
    )
    superconductors = r.unique().scalars().all()

    if not superconductors:
        # 也试归一化后的化学式
        r = await session.execute(
            select(Superconductor)
            .where(Superconductor.formula_normalized.ilike(formula))
            .options(joinedload(Superconductor.records).joinedload(SuperconductorRecord.paper))
        )
        superconductors = r.unique().scalars().all()

    result = []
    for sc in superconductors:
        records = []
        for rec in sc.records:
            if rec.paper and rec.paper.review_status == "approved":
                records.append(_format_record(rec))
        result.append({
            "type": "superconductor",
            "id": sc.id,
            "chemical_formula": sc.chemical_formula,
            "formula_normalized": sc.formula_normalized,
            "display_name": sc.display_name,
            "composition": json.loads(sc.composition) if sc.composition else {},
            "element_ratio": json.loads(sc.element_ratio) if sc.element_ratio else {},
            "records": records,
        })

    return result


async def search_by_elements_exact(
    session: AsyncSession,
    elements: list[str],
) -> list[dict]:
    """精确搜索元素体系。

    输入 ['La', 'H']，只返回 system_key='H-La' 下的超导体。
    """
    sorted_elements = sorted(elements)
    system_key = "-".join(sorted_elements)

    r = await session.execute(
        select(Superconductor)
        .join(ChemicalSystem)
        .where(ChemicalSystem.system_key == system_key)
    )
    superconductors = r.scalars().all()

    return _format_superconductors(session, superconductors)


async def search_by_elements_combination(
    session: AsyncSession,
    elements: list[str],
) -> list[dict]:
    """元素子集组合搜索。

    输入 ['La', 'H', 'S']，返回 H-La、H-S、H-La-S 下的超导体。
    """
    sorted_input = sorted(elements)
    results = []

    # 生成所有非空子集
    from itertools import combinations
    for r_len in range(1, len(sorted_input) + 1):
        for subset in combinations(sorted_input, r_len):
            system_key = "-".join(subset)
            r = await session.execute(
                select(Superconductor)
                .join(ChemicalSystem)
                .where(ChemicalSystem.system_key == system_key)
            )
            scs = r.scalars().all()
            results.extend(_format_superconductors(session, scs))

    return results


async def search_by_elements_contained(
    session: AsyncSession,
    elements: list[str],
) -> list[dict]:
    """包含搜索。

    输入 ['La', 'H']，返回 H-La、H-La-S、H-La-O 等包含 La 和 H 的所有体系。
    """
    sorted_input = sorted(elements)
    # 找到所有 system_key 包含所有这些元素的体系
    # 在 SQLite 中用 LIKE 匹配
    from sqlalchemy import and_

    conditions = []
    for elem in sorted_input:
        # system_key 格式是 "H-La-S"，每个元素前后有 -
        conditions.append(ChemicalSystem.system_key.like(f"%{elem}%"))

    r = await session.execute(
        select(ChemicalSystem)
        .where(and_(*conditions))
        .where(ChemicalSystem.element_count >= len(sorted_input))
    )
    systems = r.scalars().all()

    results = []
    for sys in systems:
        r2 = await session.execute(
            select(Superconductor)
            .where(Superconductor.chemical_system_id == sys.id)
        )
        scs = r2.scalars().all()
        results.extend(_format_superconductors(session, scs))

    return results


async def search_papers(
    session: AsyncSession,
    keyword: str,
    limit: int = 20,
) -> list[dict]:
    """搜索论文（按标题、摘要、summary 关键词匹配）。"""
    pattern = f"%{keyword}%"
    r = await session.execute(
        select(Paper)
        .where(
            (Paper.title.ilike(pattern)
             | Paper.abstract.ilike(pattern)
             | Paper.summary.ilike(pattern)
             | Paper.authors.ilike(pattern))
            & (Paper.review_status == "approved")
        )
        .limit(limit)
    )
    papers = r.scalars().all()

    return [
        {
            "type": "paper",
            "id": p.id,
            "doi": p.doi,
            "title": p.title,
            "authors": p.authors,
            "journal": p.journal,
            "year": p.year,
            "summary": p.summary,
            "paper_type": p.paper_type,
        }
        for p in papers
    ]


async def get_superconductor_records(
    session: AsyncSession,
    superconductor_id: int,
) -> list[dict]:
    """获取某个超导体的所有数据记录。"""
    from sqlalchemy.orm import joinedload

    r = await session.execute(
        select(SuperconductorRecord)
        .where(SuperconductorRecord.superconductor_id == superconductor_id)
        .options(joinedload(SuperconductorRecord.paper))
    )
    records = r.scalars().all()
    # 只返回已审核论文的记录
    records = [rec for rec in records if rec.paper and rec.paper.review_status == "approved"]
    return [_format_record(rec) for rec in records]


async def get_paper_detail(session: AsyncSession, paper_id: int) -> dict | None:
    """获取论文详情（含所有关联关键词）。"""
    from sqlalchemy.orm import joinedload

    r = await session.execute(
        select(Paper)
        .where(Paper.id == paper_id)
        .options(joinedload(Paper.records))
    )
    paper = r.unique().scalar_one_or_none()
    if not paper:
        return None

    return {
        "id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "authors": paper.authors,
        "journal": paper.journal,
        "year": paper.year,
        "abstract": paper.abstract,
        "summary": paper.summary,
        "keywords_tags": json.loads(paper.keywords_tags) if paper.keywords_tags else [],
        "paper_type": paper.paper_type,
        "source_file_path": paper.source_file_path,
        "record_count": len(paper.records),
    }


def _format_record(rec: SuperconductorRecord) -> dict:
    return {
        "id": rec.id,
        "superconductor_id": rec.superconductor_id,
        "paper_id": rec.paper_id,
        "source_label": rec.source_label,
        "article_type": rec.article_type,
        "superconductor_type": rec.superconductor_type,
        "pressure_gpa": rec.pressure_gpa,
        "space_group_symbol": rec.space_group_symbol,
        "space_group_number": rec.space_group_number,
        "crystal_structure": rec.crystal_structure,
        "thermodynamically_stable": rec.thermodynamically_stable,
        "dynamically_stable": rec.dynamically_stable,
        "energy_above_hull": rec.energy_above_hull,
        "mcmillan_tc": rec.mcmillan_tc,
        "allen_dynes_tc": rec.allen_dynes_tc,
        "experimental_tc": rec.experimental_tc,
        "lambda_value": rec.lambda_value,
        "omega_log": rec.omega_log,
        "n_ef_total": rec.n_ef_total,
        "pseudopotential_type": rec.pseudopotential_type,
        "exchange_correlation_functional": rec.exchange_correlation_functional,
        "calculation_code": rec.calculation_code,
        "k_grid": rec.k_grid,
        "q_grid": rec.q_grid,
        "energy_cutoff_value": rec.energy_cutoff_value,
        "energy_cutoff_unit": rec.energy_cutoff_unit,
        "method": rec.method,
        "data_source_note": rec.data_source_note,
        "show_in_chart": rec.show_in_chart,
        "paper_doi": rec.paper.doi if rec.paper else None,
        "paper_title": rec.paper.title if rec.paper else None,
        "paper_year": rec.paper.year if rec.paper else None,
    }


def _format_superconductors(session, superconductors) -> list[dict]:
    """（同步函数包装，仅用于内部格式化）"""
    return [
        {
            "type": "superconductor",
            "id": sc.id,
            "chemical_formula": sc.chemical_formula,
            "formula_normalized": sc.formula_normalized,
            "display_name": sc.display_name,
            "composition": json.loads(sc.composition) if sc.composition else {},
        }
        for sc in superconductors
    ]
