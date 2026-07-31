"""
HTSC-2025 JSON → MySQL
用法: python backend/scripts/migrate_htsc_to_mysql.py
"""
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "htsc2025.json"
TABLE = "htsc2025_materials"

from backend.database import DATABASE_URL as MYSQL_URL

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200),
    formula VARCHAR(200),
    class_name VARCHAR(100),
    tc FLOAT,
    elements JSON,
    composition JSON,
    INDEX idx_htsc_formula (formula),
    INDEX idx_htsc_class (class_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main():
    with open(DATA_FILE) as f:
        data = json.load(f)
    records = data.get("records", [])
    print(f"HTSC records: {len(records)}")

    engine = create_engine(MYSQL_URL)
    with engine.connect() as c:
        c.execute(text(CREATE_SQL))
        c.execute(text(f"TRUNCATE TABLE {TABLE}"))
        c.commit()

        for r in records:
            c.execute(text(f"""
                INSERT INTO {TABLE} (name, formula, class_name, tc, elements, composition)
                VALUES (:n, :f, :cls, :tc, :elem, :comp)
            """), {
                "n": r.get("name", ""),
                "f": r.get("formula", ""),
                "cls": r.get("class", ""),
                "tc": r.get("tc"),
                "elem": json.dumps(r.get("elements", [])),
                "comp": json.dumps(r.get("composition", {})),
            })
        c.commit()

    print(f"完成: {len(records)} 条")


if __name__ == "__main__":
    main()
