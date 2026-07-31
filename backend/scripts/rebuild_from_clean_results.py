"""
从 data/clean_results 重建数据库（旁路模式，不动旧库）

目标库: superconductor_dataset_v2（默认，可用 --target 覆盖）
  - papers: 旧库全量复制（含 summary/paper_type 等演进列）+ 新增 methodology/key_finding/rationale 列
  - chemical_systems / superconductors: 从 clean_results 的材料重新生成
  - key_properties: 通用物性表（取代 superconductor_records），clean_results 全部物性入库；
    物性名经 backend/prop_names.py 归一，原始写法存 name_raw，范围值保真存 value_min/value_max
  - superconductor_type: 优先继承旧库同 (paper, formula) 记录，否则按元素/压强规则推断
  - 其余表（users/periodic_table_elements/alexandria_*/htsc2025_materials/paper_chunks）原样复制

用法: PYTHONPATH=. python backend/scripts/rebuild_from_clean_results.py [--target superconductor_dataset_v2]
幂等：目标库表先 DROP 再建。
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, text

from backend.database import DATABASE_URL
from backend.ingest.prop_names import normalize_prop_name
from backend.sc_types import normalize_sc_type

CLEAN_DIR = Path(__file__).resolve().parents[2] / "data" / "clean_results"

# 与 backend/ingest/data/storer.py 保持一致的化学式解析
_FORMULA_RE = re.compile(r"([A-Z][a-z]?)(\d*\.?\d*)")


def parse_formula(formula: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for m in _FORMULA_RE.finditer(formula or ""):
        symbol, count = m.group(1), m.group(2)
        result[symbol] = result.get(symbol, 0) + (float(count) if count else 1.0)
    return result


def normalize_formula(elements: dict[str, float]) -> str:
    parts = []
    for sym in sorted(elements):
        n = elements[sym]
        n_str = str(int(n)) if float(n).is_integer() else str(n)
        parts.append(f"{sym}{n_str if n != 1 else ''}")
    return "".join(parts)


def parse_number(value) -> float | None:
    """解析单个数值：数字直取；[min,max] 与 '52-62' 取平均；其余 None"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        nums = [v for v in value if isinstance(v, (int, float))]
        return sum(nums) / len(nums) if nums else None
    if isinstance(value, str):
        m = re.findall(r"-?\d+\.?\d*", value)
        if m:
            nums = [float(x) for x in m]
            # "52-62" 会解析出 [52, -62]（负号误吸），修正为区间平均
            if len(nums) == 2 and "-" in value.strip("-"):
                return (abs(nums[0]) + abs(nums[1])) / 2
            return nums[0]
    return None


_NUM_RE = re.compile(r"-?\d+\.?\d*(?:[eE]-?\d+)?")


def parse_range(value) -> tuple[float | None, float | None, str | None]:
    """解析物性值为 (value_min, value_max, value_raw)，范围保真；无法解析时原文存 value_raw"""
    if isinstance(value, (int, float)):
        return float(value), float(value), None
    if isinstance(value, list):
        nums = [float(v) for v in value if isinstance(v, (int, float))]
        if nums:
            return min(nums), max(nums), None
        return None, None, json.dumps(value, ensure_ascii=False)[:255]
    if isinstance(value, str):
        m = _NUM_RE.findall(value)
        if m:
            nums = [float(x) for x in m]
            # "52-62" 的第二个数会被误吸负号
            if len(nums) == 2 and nums[1] < 0 <= nums[0] and "-" in value.strip("-"):
                nums[1] = abs(nums[1])
            return min(nums), max(nums), value[:255]
        return None, None, value[:255]
    return None, None, None


def extract_cond_number(cond, key) -> float | None:
    """从 condition 提取数值条件（支持 {value, unit} 与裸值；kbar → GPa）"""
    if not isinstance(cond, dict):
        return None
    v = cond.get(key)
    if isinstance(v, dict):
        num = parse_number(v.get("value"))
        if num is not None and "kbar" in str(v.get("unit") or "").lower():
            num /= 10.0
        return num
    return parse_number(v)


def infer_sc_type(elements: dict[str, float], pressure: float | None) -> str | None:
    """按元素/压强的保守规则推断超导类型；不确定时返回 None"""
    syms = set(elements)
    if "H" in syms and (pressure or 0) > 0:
        return "hydride"
    if {"Cu", "O"} <= syms:
        return "cuprate"
    if "Fe" in syms and syms & {"As", "Se", "P", "Te"}:
        return "iron_based"
    if "Ni" in syms and "O" in syms:
        return "nickel_based"
    if syms <= {"C", "B", "Ca", "K", "Rb", "Cs"} and "C" in syms:
        return "carbon"
    return None


def paper_is_experimental(paper_type) -> bool:
    return "experiment" in str(paper_type or "").lower() or "实验" in str(paper_type or "")


def sync_missing_columns(src, dst, table):
    """models 建表可能落后于旧库 alembic 演进，把旧库多出的列补到目标表"""
    with src.connect() as a, dst.connect() as b:
        # 旧库不存在的新表（如 key_properties）无需同步
        if not a.execute(text("SHOW TABLES LIKE :t"), {"t": table}).fetchone():
            return
        ddl = a.execute(text(f"SHOW CREATE TABLE `{table}`")).fetchone()[1]
        cols_src = [r[0] for r in a.execute(text(f"SHOW COLUMNS FROM `{table}`")).fetchall()]
        cols_dst = [r[0] for r in b.execute(text(f"SHOW COLUMNS FROM `{table}`")).fetchall()]
        missing = set(cols_src) - set(cols_dst)
        for line in ddl.splitlines():
            line = line.strip().rstrip(",")
            m = re.match(r"`(\w+)`\s+(.+)", line)
            if m and m.group(1) in missing:
                b.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{m.group(1)}` {m.group(2)}"))
                print(f"  {table} 补列: {m.group(1)}")
        b.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="superconductor_dataset_v2")
    args = ap.parse_args()

    src_db = DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    if args.target == src_db:
        print(f"目标库不能与源库相同: {src_db}")
        sys.exit(1)
    target_url = DATABASE_URL.replace(f"/{src_db}", f"/{args.target}")

    src = create_engine(DATABASE_URL)
    # 先用无库连接建库
    server_url = DATABASE_URL.rsplit("/", 1)[0]
    with create_engine(server_url).connect() as c:
        c.execute(text(f"CREATE DATABASE IF NOT EXISTS `{args.target}` DEFAULT CHARSET utf8mb4"))
        c.commit()
    dst = create_engine(target_url)
    print(f"源库: {src_db} → 目标库: {args.target}")

    # ── 1. 清空目标库（禁外键绕过 paper_chunks→papers 等依赖）并重建同构表 ──
    from backend import models
    with dst.connect() as c:
        c.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for (t,) in c.execute(text("SHOW TABLES")).fetchall():
            c.execute(text(f"DROP TABLE IF EXISTS `{t}`"))
        c.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        c.commit()
    models.Base.metadata.create_all(dst)
    # 补齐旧库经 alembic 演进而 models 未同步的列（如 papers.summary/paper_type）
    for t in models.Base.metadata.tables:
        sync_missing_columns(src, dst, t)
    with dst.connect() as c:
        # papers 新增 clean_results 结构化列
        for col in ("methodology", "key_finding", "rationale"):
            c.execute(text(f"ALTER TABLE papers ADD COLUMN {col} TEXT"))
        # v2 以 key_properties 取代 superconductor_records
        c.execute(text("DROP TABLE IF EXISTS superconductor_records"))
        c.commit()
    print("目标库表结构已创建（papers 含 methodology/key_finding/rationale；records 已由 key_properties 取代）")

    # ── 2. 原样复制的表 ──
    copy_tables = ["users", "periodic_table_elements", "papers", "paper_chunks",
                   "alexandria_entries", "alexandria_element_idx", "htsc2025_materials"]
    with src.connect() as sc_, dst.connect() as dc:
        existing = {r[0] for r in dc.execute(text("SHOW TABLES")).fetchall()}
        # models 未管理的表（paper_chunks/alexandria/htsc）按源表 DDL 创建
        for t in copy_tables:
            if t not in existing:
                ddl = sc_.execute(text(f"SHOW CREATE TABLE `{t}`")).fetchone()[1]
                dc.execute(text(ddl))
        dc.commit()
    for t in copy_tables:
        with src.connect() as sc_, dst.connect() as dc:
            # users 存在自引用外键（approved_by_user_id），批量复制期间禁用外键检查
            dc.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            cols = [r[0] for r in sc_.execute(text(f"SHOW COLUMNS FROM `{t}`")).fetchall()]
            # papers 目标表多 3 列，交集复制
            dst_cols = [r[0] for r in dc.execute(text(f"SHOW COLUMNS FROM `{t}`")).fetchall()]
            use = [c for c in cols if c in dst_cols]
            col_list = ",".join(f"`{c}`" for c in use)
            rows = sc_.execute(text(f"SELECT {col_list} FROM `{t}`")).fetchall()
            if rows:
                placeholders = ",".join(f":c{i}" for i in range(len(use)))
                dc.execute(
                    text(f"INSERT INTO `{t}` ({col_list}) VALUES ({placeholders})"),
                    [{f"c{i}": v for i, v in enumerate(r)} for r in rows],
                )
            dc.commit()
            print(f"复制 {t}: {len(rows)} 行")

    # ── 3. 旧库类型继承索引: (paper_id, formula_normalized) → superconductor_type ──
    legacy_types: dict[tuple, str] = {}
    with src.connect() as c:
        rows = c.execute(text("""
            SELECT r.paper_id, s.formula_normalized, r.superconductor_type
            FROM superconductor_records r JOIN superconductors s ON s.id = r.superconductor_id
            WHERE r.superconductor_type IS NOT NULL
        """)).fetchall()
    for pid, fn, st in rows:
        norm = normalize_sc_type(st)
        if norm:
            legacy_types.setdefault((pid, fn), norm)
    print(f"旧库类型索引: {len(legacy_types)} 组")

    # ── 4. 遍历 clean_results 生成 key_properties（全部物性入库）──
    stats = Counter()
    type_src = Counter()
    sys_ids: dict[str, int] = {}
    sc_ids: dict[str, int] = {}

    with dst.connect() as dc:
        for f in sorted(CLEAN_DIR.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0):
            if not f.stem.isdigit():
                continue
            paper_id = int(f.stem)
            try:
                data = json.loads(f.read_text())
            except Exception:
                stats["json 解析失败"] += 1
                continue

            # papers 补充列
            dc.execute(text("""
                UPDATE papers SET methodology = :m, key_finding = :k, rationale = :r WHERE id = :i
            """), {
                "m": json.dumps(data.get("methodology"), ensure_ascii=False) if data.get("methodology") is not None else None,
                "k": json.dumps(data.get("key_finding"), ensure_ascii=False) if data.get("key_finding") is not None else None,
                "r": json.dumps(data.get("rationale"), ensure_ascii=False) if data.get("rationale") is not None else None,
                "i": paper_id,
            })

            # key_properties 统一为 {material: [props]}
            kp = data.get("key_properties")
            if isinstance(kp, list):
                rms = data.get("research_materials") or []
                if len(rms) == 1 and isinstance(rms[0], str):
                    kp = {rms[0]: kp}
                else:
                    stats["list 形态无法定位材料，跳过"] += 1
                    continue
            if not isinstance(kp, dict):
                stats["无 key_properties"] += 1
                continue

            is_exp = paper_is_experimental(data.get("paper_type"))

            for material, props in kp.items():
                if not isinstance(props, list) or not isinstance(material, str):
                    continue
                material = material.strip()[:255]

                # 能解析为化学式的材料建立实体并关联；否则仅保留原名
                elements = parse_formula(material)
                sc_id = None
                formula_norm = None
                if elements:
                    system_key = "-".join(sorted(elements))
                    formula_norm = normalize_formula(elements)
                    if system_key not in sys_ids:
                        dc.execute(text("""
                            INSERT INTO chemical_systems (system_key, elements_list, element_count, created_at, updated_at)
                            VALUES (:k, :e, :n, NOW(), NOW())
                        """), {"k": system_key, "e": json.dumps(sorted(elements)), "n": len(elements)})
                        sys_ids[system_key] = dc.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    if formula_norm not in sc_ids:
                        total = sum(elements.values()) or 1.0
                        ratio = {k: round(v / total, 6) for k, v in elements.items()}
                        dc.execute(text("""
                            INSERT INTO superconductors
                                (chemical_system_id, chemical_formula, formula_normalized, display_name,
                                 elements_list, composition, element_ratio, created_at, updated_at)
                            VALUES (:cs, :f, :fn, :f, :el, :comp, :ratio, NOW(), NOW())
                        """), {"cs": sys_ids[system_key], "f": material, "fn": formula_norm,
                               "el": json.dumps(sorted(elements)), "comp": json.dumps(elements),
                               "ratio": json.dumps(ratio)})
                        sc_ids[formula_norm] = dc.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    sc_id = sc_ids[formula_norm]
                else:
                    stats["材料名非化学式（不关联实体）"] += 1

                # 材料级超导类型：继承旧库 → 规则推断（参考该材料物性中的最大压强）
                max_pressure = max(
                    (extract_cond_number(p.get("condition"), "pressure") or 0)
                    for p in props if isinstance(p, dict)
                ) if any(isinstance(p, dict) for p in props) else None
                sc_type = legacy_types.get((paper_id, formula_norm)) if formula_norm else None
                if sc_type:
                    type_src["继承旧库"] += 1
                elif elements:
                    sc_type = infer_sc_type(elements, max_pressure)
                    type_src["规则推断" if sc_type else "无法确定(NULL)"] += 1
                else:
                    type_src["无法确定(NULL)"] += 1

                for p in props:
                    if not isinstance(p, dict):
                        stats["物性条目非字典，跳过"] += 1
                        continue
                    name_raw = str(p.get("name") or "").strip()[:255]
                    if not name_raw:
                        stats["物性无名称，跳过"] += 1
                        continue
                    name, matched = normalize_prop_name(name_raw)
                    stats["名称归一命中" if matched else "名称保留原名"] += 1
                    vmin, vmax, vraw = parse_range(p.get("value"))
                    cond = p.get("condition") if isinstance(p.get("condition"), dict) else None

                    dc.execute(text("""
                        INSERT INTO key_properties
                            (paper_id, superconductor_id, material, name, name_raw, name_note,
                             value_min, value_max, value_raw, unit, pressure_gpa, temperature_k,
                             condition_json, condition_note, is_primary, superconductor_type,
                             article_type, source_label, created_at, updated_at)
                        VALUES (:pid, :scid, :mat, :name, :nraw, :nnote,
                                :vmin, :vmax, :vraw, :unit, :pg, :tk,
                                :cj, :cnote, :prim, :st, :at, 'clean_results', NOW(), NOW())
                    """), {
                        "pid": paper_id, "scid": sc_id, "mat": material,
                        "name": name[:100], "nraw": name_raw,
                        "nnote": (str(p.get("name_note"))[:500] if p.get("name_note") else None),
                        "vmin": vmin, "vmax": vmax, "vraw": vraw,
                        "unit": (str(p.get("unit"))[:50] if p.get("unit") else None),
                        "pg": extract_cond_number(cond, "pressure"),
                        "tk": extract_cond_number(cond, "temperature"),
                        "cj": json.dumps(cond, ensure_ascii=False) if cond else None,
                        "cnote": (str(p.get("condition_note")) or None) if p.get("condition_note") else None,
                        "prim": bool(p.get("is_primary")),
                        "st": sc_type, "at": "e" if is_exp else "t",
                    })
                    stats["物性入库"] += 1
        dc.commit()

    print("\n=== 重建完成 ===")
    for k, v in stats.most_common():
        print(f"  {k}: {v}")
    print("类型来源:", dict(type_src))
    with dst.connect() as c:
        for t in ("papers", "chemical_systems", "superconductors", "key_properties"):
            print(f"  目标库 {t}: {c.execute(text(f'SELECT COUNT(*) FROM `{t}`')).scalar()} 行")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"总耗时 {time.time()-t0:.1f}s")
