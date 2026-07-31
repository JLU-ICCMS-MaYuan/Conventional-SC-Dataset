"""
从 MySQL data_json 批量生成 CIF 结构文本，写入 alexandria_entries.structure_cif 列
（不依赖 SQLite 源库；结构由 dyns 的 ibrav/celldm/sites 重建，空间群用 spglib 计算）

用法: PYTHONPATH=. python backend/scripts/backfill_alexandria_cif.py
幂等：默认只处理 structure_cif 为 NULL 的行，--force 重新生成全部。
"""
import json
import sys
import time

from sqlalchemy import text

from backend.database import engine
from backend.services.alexandria_mysql import compute_structure, structure_to_cif

BATCH = 500


def main(force: bool = False):
    cond = "" if force else "AND structure_cif IS NULL"
    with engine.connect() as c:
        ids = [r[0] for r in c.execute(text(
            f"SELECT id FROM alexandria_entries WHERE data_json IS NOT NULL {cond}"
        )).fetchall()]
    print(f"待生成 CIF: {len(ids)}")

    t0 = time.time()
    done = ok = 0
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT id, formula, data_json FROM alexandria_entries "
                f"WHERE id IN ({','.join(str(x) for x in chunk)})"
            )).fetchall()

            updates = []
            for eid, formula, dj in rows:
                cif = None
                try:
                    structure = compute_structure(json.loads(dj))
                    cif = structure_to_cif(structure, formula) if structure else None
                except Exception:
                    pass
                if cif:
                    ok += 1
                updates.append({"i": eid, "cif": cif})

            c.execute(text(
                "UPDATE alexandria_entries SET structure_cif = :cif WHERE id = :i"
            ), updates)
            c.commit()

        done += len(rows)
        if (i // BATCH) % 10 == 0:
            print(f"  进度: {done}/{len(ids)} | CIF 成功 {ok} | {time.time()-t0:.0f}s")

    print(f"完成: {done} 条 | CIF 成功 {ok} | 总耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
