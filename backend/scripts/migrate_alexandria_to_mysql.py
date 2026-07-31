"""
Alexandria SQLite → MySQL（仅迁有 Tc 数据的条目）
用法: PYTHONPATH=. python backend/scripts/migrate_alexandria_to_mysql.py
"""
import json
import sqlite3
import time
from pathlib import Path

from sqlalchemy import create_engine, text

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "alexandria"
SQLITE_DB = DATA_DIR / "alexandria.db"

from backend.database import DATABASE_URL as MYSQL_URL

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS alexandria_entries (
    id INT PRIMARY KEY,
    mat_id VARCHAR(100) UNIQUE,
    filename VARCHAR(200),
    formula VARCHAR(200),
    elements JSON,
    nsites INT,
    spg INT,
    lambda_val DOUBLE,
    tc_max DOUBLE,
    imag TINYINT(1) DEFAULT 1,
    band_gap DOUBLE,
    dos_ef DOUBLE,
    e_above_hull DOUBLE,
    e_form DOUBLE,
    energy_total DOUBLE,
    tc_mcmillan DOUBLE,
    tc_allen_dynes DOUBLE,
    tc_eliashberg DOUBLE,
    wlog DOUBLE,
    integral_a2f DOUBLE,
    stress_xx DOUBLE,
    stress_yy DOUBLE,
    stress_zz DOUBLE,
    data_json LONGTEXT,
    INDEX idx_aelx_formula (formula),
    INDEX idx_aelx_tc_max (tc_max)
);

CREATE TABLE IF NOT EXISTS alexandria_element_idx (
    element VARCHAR(5) NOT NULL,
    entry_id INT NOT NULL,
    PRIMARY KEY (element, entry_id),
    INDEX idx_aelx_el (element)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def main():
    if not SQLITE_DB.exists():
        print(f"SQLite 数据库不存在: {SQLITE_DB}")
        return

    engine = create_engine(MYSQL_URL)
    with engine.connect() as c:
        for stmt in CREATE_SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                c.execute(text(stmt))
        c.commit()
    print("MySQL 表已创建")

    src = sqlite3.connect(str(SQLITE_DB))
    total = src.execute(
        "SELECT COUNT(*) FROM entries WHERE tc_max IS NOT NULL"
    ).fetchone()[0]
    print(f"SQLite entries (有Tc): {total}")

    BATCH = 500
    t0 = time.time()
    copied = 0
    for offset in range(0, total, BATCH):
        rows = src.execute(
            "SELECT id, mat_id, filename, formula, elements, nsites, spg, "
            "lambda_val, tc_max, imag, band_gap, dos_ef, e_above_hull, "
            "e_form, energy_total, tc_mcmillan, tc_allen_dynes, "
            "tc_eliashberg, wlog, integral_a2f, "
            "stress_xx, stress_yy, stress_zz FROM entries "
            "WHERE tc_max IS NOT NULL "
            "ORDER BY id LIMIT ? OFFSET ?",
            (BATCH, offset)
        ).fetchall()

        with engine.connect() as c:
            for r in rows:
                els = r[4]
                if isinstance(els, str):
                    try:
                        json.loads(els)
                    except Exception:
                        els = json.dumps([])

                c.execute(text("""
                    INSERT INTO alexandria_entries
                        (id, mat_id, filename, formula, elements, nsites, spg,
                         lambda_val, tc_max, imag, band_gap, dos_ef,
                         e_above_hull, e_form, energy_total,
                         tc_mcmillan, tc_allen_dynes, tc_eliashberg,
                         wlog, integral_a2f, stress_xx, stress_yy, stress_zz)
                    VALUES (:id, :mat_id, :fn, :f, :el, :ns, :spg,
                            :lv, :tc, :im, :bg, :dos,
                            :eah, :ef, :et,
                            :tcm, :tca, :tce, :wl, :ia2f, :sx, :sy, :sz)
                    ON DUPLICATE KEY UPDATE formula=VALUES(formula)
                """), {
                    "id": r[0], "mat_id": r[1], "fn": r[2], "f": r[3],
                    "el": els, "ns": r[5], "spg": r[6],
                    "lv": r[7], "tc": r[8], "im": r[9], "bg": r[10],
                    "dos": r[11], "eah": r[12], "ef": r[13], "et": r[14],
                    "tcm": r[15], "tca": r[16], "tce": r[17],
                    "wl": r[18], "ia2f": r[19],
                    "sx": r[20], "sy": r[21], "sz": r[22],
                })
            c.commit()

        copied += len(rows)
        if (offset // BATCH) % 20 == 0:
            print(f"  entries: {copied}/{total} ({time.time()-t0:.0f}s)")

    print(f"entries 完成: {copied} 条, {time.time()-t0:.0f}s")

    # ── 元素索引（只迁已导入的 entry） ──
    with engine.connect() as c:
        entry_ids = set(
            r[0] for r in c.execute(text("SELECT id FROM alexandria_entries")).fetchall()
        )

    idx_total = src.execute(
        "SELECT COUNT(*) FROM element_idx WHERE entry_id IN "
        f"({','.join(str(eid) for eid in list(entry_ids)[:1000])})"
    ).fetchone()[0]
    print(f"element_idx rows to copy: ~{idx_total}+")

    t1 = time.time()
    idx_copied = 0
    batch_ids = list(entry_ids)

    for i in range(0, len(batch_ids), 1000):
        chunk = batch_ids[i:i+1000]
        placeholders = ",".join("?" for _ in chunk)
        rows = src.execute(
            f"SELECT element, entry_id FROM element_idx WHERE entry_id IN ({placeholders})",
            chunk
        ).fetchall()

        with engine.connect() as c:
            for el, eid in rows:
                try:
                    c.execute(text(
                        "INSERT IGNORE INTO alexandria_element_idx (element, entry_id) VALUES (:el, :eid)"
                    ), {"el": el, "eid": eid})
                except Exception:
                    pass
            c.commit()
        idx_copied += len(rows)
        if (i // 1000) % 20 == 0:
            print(f"  element_idx: {idx_copied} ({time.time()-t1:.0f}s)")

    src.close()
    print(f"element_idx 完成: {idx_copied} 条, {time.time()-t1:.0f}s")

    # 统计
    with engine.connect() as c:
        e_cnt = c.execute(text("SELECT COUNT(*) FROM alexandria_entries")).scalar()
        i_cnt = c.execute(text("SELECT COUNT(*) FROM alexandria_element_idx")).scalar()
    print(f"\nMySQL: {e_cnt} entries, {i_cnt} element_idx")


if __name__ == "__main__":
    main()
