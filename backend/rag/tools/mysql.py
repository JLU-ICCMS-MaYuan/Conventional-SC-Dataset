"""
knowledge_graph.py — 知识图谱查询模块。

使用 SQLAlchemy async 查询 key_properties / superconductors / papers。
支持 MySQL 和 SQLite，由 RAG_DATABASE_URL 配置决定。

v2 起数据源为通用物性表 key_properties（每行一条物性），
谓词映射到规范物性名（backend/prop_names.py），并保留数值范围、单位与条件。
"""

from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.sql import func

from backend.ingest.prop_names import PROP_LABELS
from backend.rag.database import async_session_factory
from backend.models import KeyProperty, Paper

# 中文谓词 → 规范物性名
PREDICATE_MAP = {
    "超导温度(AD)": "critical_temperature",
    "超导温度": "critical_temperature",
    "临界温度": "critical_temperature",
    "电声耦合lambda": "electron_phonon_coupling",
    "电声耦合": "electron_phonon_coupling",
    "德拜温度": "debye_temperature",
    "上临界磁场": "upper_critical_field",
    "超导能隙": "superconducting_gap",
}


async def query(
    predicate: str,
    operator: str = "=",
    value: str | None = None,
) -> list[dict]:
    """查询知识图谱。

    predicate 映射到 key_properties 的规范物性名：
      "超导温度(AD)" → name='critical_temperature'
      "电声耦合lambda"   → name='electron_phonon_coupling'
      "压力"         → key_properties.pressure_gpa（条件列，特判）

    Returns:
        类型化物性记录，包含数值范围、单位、压力、温度和完整条件。
    """
    if predicate == "压力":
        # 压力是物性的条件列而非独立物性行
        field = KeyProperty.pressure_gpa
        name_filter = None
    else:
        canonical = PREDICATE_MAP.get(predicate)
        if canonical is None:
            return []
        field = KeyProperty.value_max
        name_filter = canonical

    async with async_session_factory() as session:
        stmt = (
            select(
                KeyProperty.material,
                KeyProperty.name,
                KeyProperty.value_min,
                KeyProperty.value_max,
                KeyProperty.value_raw,
                KeyProperty.unit,
                KeyProperty.pressure_gpa,
                KeyProperty.temperature_k,
                KeyProperty.condition_json,
                KeyProperty.condition_note,
                Paper.id,
                Paper.title,
            )
            .select_from(KeyProperty)
            .join(Paper, Paper.id == KeyProperty.paper_id)
            .where(field.isnot(None))
            .where(Paper.review_status == "approved")
        )
        if name_filter:
            stmt = stmt.where(KeyProperty.name == name_filter)

        if operator in (">", "<", ">=", "<=") and value is not None:
            try:
                val = float(value)
            except ValueError:
                return []
            if operator == ">":
                stmt = stmt.where(field > val)
            elif operator == "<":
                stmt = stmt.where(field < val)
            elif operator == ">=":
                stmt = stmt.where(field >= val)
            elif operator == "<=":
                stmt = stmt.where(field <= val)
        elif operator == "=" and value:
            try:
                val = float(value)
            except ValueError:
                return []
            stmt = stmt.where(field == val)

        stmt = stmt.order_by(field.desc()).distinct()

        result = await session.execute(stmt)
        rows = result.all()

    records = []
    for row in rows:
        condition = row.condition_json
        if isinstance(condition, str):
            try:
                condition = json.loads(condition)
            except json.JSONDecodeError:
                pass
        records.append({
            "subject": row.material,
            "predicate": predicate,
            "property_name": row.name,
            "value_min": row.value_min,
            "value_max": row.value_max,
            "value_raw": row.value_raw,
            "unit": row.unit,
            "pressure_gpa": row.pressure_gpa,
            "temperature_k": row.temperature_k,
            "condition": condition,
            "condition_note": row.condition_note,
            "paper_id": row.id,
            "paper_title": row.title,
        })
    return records


async def get_all_properties(subject: str) -> list[dict]:
    """获取某超导体/材料的全部物性（每行一条，含条件与备注）。"""
    async with async_session_factory() as session:
        stmt = (
            select(KeyProperty)
            .join(Paper, Paper.id == KeyProperty.paper_id)
            .where(KeyProperty.material == subject)
            .where(Paper.review_status == "approved")
        )
        result = await session.execute(stmt)
        props = result.scalars().all()

    out = []
    for kp in props:
        if kp.value_max is None and not kp.value_raw:
            continue
        if kp.value_min is not None and kp.value_min != kp.value_max:
            value = f"{kp.value_min}-{kp.value_max}"
        else:
            value = str(kp.value_max) if kp.value_max is not None else kp.value_raw
        obj = f"{value} {kp.unit}" if kp.unit else value
        if kp.pressure_gpa is not None:
            obj += f" @ {kp.pressure_gpa} GPa"
        out.append({
            "predicate": PROP_LABELS.get(kp.name, kp.name),
            "object": obj,
            "note": kp.name_note,
        })
    return out


async def delete_paper_triples(paper_id: int) -> int:
    """删除某篇论文的数据。"""
    async with async_session_factory() as session:
        stmt = delete(KeyProperty).where(KeyProperty.paper_id == paper_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def stats() -> dict:
    """返回知识图谱统计信息。"""
    async with async_session_factory() as session:
        subj_stmt = (
            select(func.count(func.distinct(KeyProperty.material)))
            .select_from(KeyProperty)
            .join(Paper, Paper.id == KeyProperty.paper_id)
            .where(Paper.review_status == "approved")
        )
        subjects = (await session.execute(subj_stmt)).scalar() or 0

        prop_stmt = (
            select(func.count())
            .select_from(KeyProperty)
            .join(Paper, Paper.id == KeyProperty.paper_id)
            .where(Paper.review_status == "approved")
        )
        triples = (await session.execute(prop_stmt)).scalar() or 0

    return {"subjects": subjects, "triples": triples}
