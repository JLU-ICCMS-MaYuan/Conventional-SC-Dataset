"""
补全 Alexandria MySQL 表的 spg / stress_* / data_json 字段
（原迁移脚本只迁了标量列；spg 在源数据中不存在，需从 dyns 结构用 spglib 计算；
 stress 在 data JSON 中为 Voigt 列表；data_json 为剥离大矩阵后的轻量原始数据）

用法: PYTHONPATH=. python backend/scripts/backfill_alexandria_structure.py
幂等：可重复执行，按 mat_id UPDATE。
"""
import json
import sqlite3
import time
from pathlib import Path

from sqlalchemy import text

from backend.database import engine
from backend.services.alexandria_mysql import compute_structure, strip_heavy

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "alexandria"
SQLITE_DB = DATA_DIR / "alexandria.db"

BATCH = 200


def main():
    if not SQLITE_DB.exists():
        print(f"SQLite 数据库不存在: {SQLITE_DB}")
        return

    with engine.connect() as c:
        mat_ids = [r[0] for r in c.execute(text("SELECT mat_id FROM alexandria_entries")).fetchall()]
    print(f"MySQL 待补全条目: {len(mat_ids)}")

    src = sqlite3.connect(str(SQLITE_DB))
    t0 = time.time()
    done = spg_ok = struct_fail = 0

    for i in range(0, len(mat_ids), BATCH):
        chunk = mat_ids[i:i + BATCH]
        placeholders = ",".join("?" for _ in chunk)
        rows = src.execute(
            f"SELECT mat_id, data FROM entries WHERE mat_id IN ({placeholders})", chunk
        ).fetchall()

        updates = []
        for mat_id, raw in rows:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            stress = data.get("stress")
            sxx = syy = szz = None
            if isinstance(stress, list) and len(stress) >= 3:
                sxx, syy, szz = stress[0], stress[1], stress[2]

            spg = None
            structure = compute_structure(data)
            if structure:
                spg = structure["spg_number"]
                if spg:
                    spg_ok += 1
            else:
                struct_fail += 1

            updates.append({
                "m": mat_id, "spg": spg,
                "sx": sxx, "sy": syy, "sz": szz,
                "dj": json.dumps(strip_heavy(data), ensure_ascii=False),
            })

        with engine.connect() as c:
            c.execute(text("""
                UPDATE alexandria_entries
                SET spg = :spg, stress_xx = :sx, stress_yy = :sy, stress_zz = :sz,
                    data_json = :dj
                WHERE mat_id = :m
            """), updates)
            c.commit()

        done += len(rows)
        if (i // BATCH) % 10 == 0:
            print(f"  进度: {done}/{len(mat_ids)} | spg 成功 {spg_ok} | 无结构 {struct_fail} | {time.time()-t0:.0f}s")

    print(f"完成: {done} 条 | spg 成功 {spg_ok} | 无结构 {struct_fail} | 总耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
