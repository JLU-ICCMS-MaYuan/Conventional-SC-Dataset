"""
knowledge_graph.py — 知识图谱查询模块。

使用 SQLAlchemy async 查询 superconductor_records / superconductors / papers。
支持 MySQL 和 SQLite，由 RAG_DATABASE_URL 配置决定。
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.sql import func

from backend.rag.database import async_session_factory
from backend.rag.models import Paper, Superconductor, SuperconductorRecord

FIELD_MAP = {
    "超导温度(AD)": SuperconductorRecord.allen_dynes_tc,
    "压力": SuperconductorRecord.pressure_gpa,
    "电声耦合lambda": SuperconductorRecord.lambda_value,
}


async def query(
    predicate: str,
    operator: str = "=",
    value: str | None = None,
) -> list[dict]:
    """查询知识图谱。

    predicate 映射到数据库字段：
      "超导温度(AD)" → superconductor_records.allen_dynes_tc
      "压力"         → superconductor_records.pressure_gpa
      "电声耦合lambda"   → superconductor_records.lambda_value

    Returns:
        [{"subject": "LaH10", "predicate": "超导温度(AD)", "object": "250"}, ...]
    """
    field = FIELD_MAP.get(predicate)
    if field is None:
        return []

    async with async_session_factory() as session:
        stmt = (
            select(
                Superconductor.chemical_formula,
                field,
                Paper.id,
                Paper.title,
            )
            .select_from(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(field.isnot(None))
            .where(Paper.review_status == "approved")
        )

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

    return [
        {
            "subject": row.chemical_formula,
            "predicate": predicate,
            "object": str(row[1]),
            "paper_id": row[2],
            "paper_title": row[3],
        }
        for row in rows
    ]


async def get_all_properties(subject: str) -> list[dict]:
    """获取某超导体的所有属性。"""
    async with async_session_factory() as session:
        stmt = (
            select(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Superconductor.chemical_formula == subject)
            .where(Paper.review_status == "approved")
            .limit(1)
        )
        result = await session.execute(stmt)
        rec = result.scalars().first()

    if rec is None:
        return []

    labels = [
        ("超导温度(AD)", "allen_dynes_tc"),
        ("实验Tc", "experimental_tc"),
        ("压力", "pressure_gpa"),
        ("电声耦合lambda", "lambda_value"),
        ("声子频率ω_log", "omega_log"),
        ("空间群", "space_group_symbol"),
    ]
    props = []
    for label, key in labels:
        val = getattr(rec, key, None)
        if val is not None:
            props.append({"predicate": label, "object": str(val)})
    return props


async def delete_paper_triples(paper_id: int) -> int:
    """删除某篇论文的数据。"""
    async with async_session_factory() as session:
        stmt = delete(SuperconductorRecord).where(SuperconductorRecord.paper_id == paper_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def stats() -> dict:
    """返回知识图谱统计信息。"""
    async with async_session_factory() as session:
        subj_stmt = (
            select(func.count(func.distinct(Superconductor.chemical_formula)))
            .select_from(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Paper.review_status == "approved")
        )
        subjects = (await session.execute(subj_stmt)).scalar() or 0

        rec_stmt = (
            select(func.count())
            .select_from(SuperconductorRecord)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Paper.review_status == "approved")
        )
        records = (await session.execute(rec_stmt)).scalar() or 0

    return {"subjects": subjects, "triples": records}
