"""
knowledge_graph.py — 知识图谱查询模块。

直接查 dev.db 的现有表（superconductor_records / superconductors / papers），
不需要单独建表存储。查询逻辑和"知识图谱"概念一致，数据源是已有的关系表。
"""

from __future__ import annotations

import sqlite3

from backend.rag.config import get_rag_settings


def _conn():
    db_path = get_rag_settings().data_root / "dev.db"
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def query(predicate: str, operator: str = "=", value: str | None = None) -> list[dict]:
    """查询知识图谱。

    predicate 映射到数据库字段：
      "超导温度(AD)" → superconductor_records.allen_dynes_tc
      "压力"         → superconductor_records.pressure_gpa
      "电声耦合lambda"   → superconductor_records.lambda_value

    Args:
        predicate: "超导温度(AD)" / "压力" / "电声耦合lambda"
        operator: "=", ">", "<", ">=", "<="
        value: 比较值

    Returns:
        [{"subject": "LaH10", "predicate": "超导温度(AD)", "object": "250"}, ...]
    """
    field_map = {
        "超导温度(AD)": "sr.allen_dynes_tc",
        "压力": "sr.pressure_gpa",
        "电声耦合lambda": "sr.lambda_value",
    }

    field = field_map.get(predicate)
    if not field:
        return []

    conn = _conn()

    if operator in (">", "<", ">=", "<=") and value is not None:
        try:
            val = float(value)
        except ValueError:
            conn.close()
            return []
        op = operator
        sql = f"""
            SELECT DISTINCT sc.chemical_formula AS formula, {field} AS val,
                   p.id AS paper_id, p.title AS paper_title
            FROM superconductor_records sr
            JOIN superconductors sc ON sc.id = sr.superconductor_id
            JOIN papers p ON p.id = sr.paper_id
            WHERE {field} IS NOT NULL
              AND {field} {op} ?
              AND p.review_status = 'approved'
            ORDER BY {field} DESC
        """
        rows = conn.execute(sql, (val,)).fetchall()
    elif operator == "=" and value:
        sql = f"""
            SELECT DISTINCT sc.chemical_formula, {field} AS val,
                   p.id AS paper_id, p.title AS paper_title
            FROM superconductor_records sr
            JOIN superconductors sc ON sc.id = sr.superconductor_id
            JOIN papers p ON p.id = sr.paper_id
            WHERE {field} = ?
              AND p.review_status = 'approved'
        """
        rows = conn.execute(sql, (float(value) if value.replace(".", "", 1).isdigit() else value,)).fetchall()
    else:
        sql = f"""
            SELECT DISTINCT sc.chemical_formula, {field} AS val,
                   p.id AS paper_id, p.title AS paper_title
            FROM superconductor_records sr
            JOIN superconductors sc ON sc.id = sr.superconductor_id
            JOIN papers p ON p.id = sr.paper_id
            WHERE {field} IS NOT NULL
              AND p.review_status = 'approved'
        """
        rows = conn.execute(sql).fetchall()

    conn.close()
    return [
        {
            "subject": r["formula"],
            "predicate": predicate,
            "object": str(r["val"]),
            "paper_id": r["paper_id"],
            "paper_title": r["paper_title"],
        }
        for r in rows
    ]


def get_all_properties(subject: str) -> list[dict]:
    """获取某超导体的所有属性。"""
    conn = _conn()
    rows = conn.execute("""
        SELECT sr.allen_dynes_tc, sr.experimental_tc, sr.pressure_gpa,
               sr.lambda_value, sr.omega_log, sr.space_group_symbol
        FROM superconductor_records sr
        JOIN superconductors sc ON sc.id = sr.superconductor_id
        JOIN papers p ON p.id = sr.paper_id
        WHERE sc.chemical_formula = ?
          AND p.review_status = 'approved'
        LIMIT 1
    """, (subject,)).fetchall()
    conn.close()

    props = []
    labels = [
        ("超导温度(AD)", "allen_dynes_tc"),
        ("实验Tc", "experimental_tc"),
        ("压力", "pressure_gpa"),
        ("电声耦合lambda", "lambda_value"),
        ("声子频率ω_log", "omega_log"),
        ("空间群", "space_group_symbol"),
    ]
    if rows:
        r = rows[0]
        for label, key in labels:
            val = r[key]
            if val is not None:
                props.append({"predicate": label, "object": str(val)})
    return props


def delete_paper_triples(paper_id: int) -> int:
    """删除某篇论文的数据（等价于删除对应的 superconductor_records）。"""
    conn = _conn()
    cur = conn.execute("DELETE FROM superconductor_records WHERE paper_id = ?", (paper_id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected


def stats() -> dict:
    """返回知识图谱统计信息（基于现有表）。"""
    conn = _conn()
    subjects = conn.execute("""
        SELECT COUNT(DISTINCT sc.chemical_formula)
        FROM superconductors sc
        JOIN superconductor_records sr ON sr.superconductor_id = sc.id
        JOIN papers p ON p.id = sr.paper_id
        WHERE p.review_status = 'approved'
    """).fetchone()[0]
    records = conn.execute("""
        SELECT COUNT(*) FROM superconductor_records sr
        JOIN papers p ON p.id = sr.paper_id
        WHERE p.review_status = 'approved'
    """).fetchone()[0]
    conn.close()
    return {"subjects": subjects, "triples": records}
