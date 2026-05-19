"""
将 Alexandria 原始 JSON 数据导入 SQLite 数据库
保留完整原始数据 + 元素索引，支持快速元素查找
"""
import json
import os
import sqlite3
import time
import sys
from typing import List, Set, Dict, Any, Optional

ALEXANDRIA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "alexandria"
)
DB_PATH = os.path.join(ALEXANDRIA_DIR, "alexandria.db")


# 只读连接缓存（线程安全，WAL 模式支持并发读）
_read_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    """获取写入连接（用于导入）"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=OFF")        # 批量导入禁用 WAL
    conn.execute("PRAGMA synchronous=OFF")          # 关闭同步写入
    conn.execute("PRAGMA cache_size=-8000000")      # 8GB 缓存
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def get_read_conn() -> sqlite3.Connection:
    """获取只读连接（用于 API 查询，缓存复用）"""
    global _read_conn
    if _read_conn is None:
        _read_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _read_conn.execute("PRAGMA journal_mode=WAL")     # WAL 模式支持并发读
        _read_conn.execute("PRAGMA cache_size=-200000")    # 200MB 缓存
        _read_conn.execute("PRAGMA temp_store=MEMORY")
    return _read_conn


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        DROP TABLE IF EXISTS element_idx;
        DROP TABLE IF EXISTS entries;

        CREATE TABLE entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mat_id      TEXT UNIQUE NOT NULL,
            filename    TEXT NOT NULL,
            formula     TEXT,
            elements    TEXT,               -- JSON 数组 ["H","Mo","Nb"]
            nsites      INTEGER,
            spg         INTEGER,
            lambda_val  REAL,
            tc_max      REAL,
            imag        INTEGER,            -- 0=稳定, 1=虚声子
            band_gap    REAL,
            dos_ef      REAL,
            e_above_hull REAL,
            e_form      REAL,
            energy_total REAL,
            data        TEXT NOT NULL       -- 完整原始 JSON
        );

        CREATE INDEX idx_entries_formula ON entries(formula);
        CREATE INDEX idx_entries_tc_max  ON entries(tc_max);
        CREATE INDEX idx_entries_imag    ON entries(imag);

        CREATE TABLE element_idx (
            element  TEXT NOT NULL,
            entry_id INTEGER NOT NULL,
            PRIMARY KEY (element, entry_id)
        ) WITHOUT ROWID;
    """)
    conn.commit()


def _extract_tc_max(tc_data) -> Optional[float]:
    """从 tc 字段提取最大 Tc 值"""
    if not tc_data or not isinstance(tc_data, dict):
        return None
    tc_max = 0.0
    for key in ("TcMcMillan", "TcAllenDynes"):
        vals = tc_data.get(key)
        if isinstance(vals, list):
            clean = [v for v in vals if v is not None]
            if clean:
                tc_max = max(max(clean), tc_max)
    return round(tc_max, 2) if tc_max > 0 else None


def _extract_meta(d: Dict) -> Dict:
    """提取建索引所需的元数据字段"""
    tc = d.get("tc", {}) or {}
    return {
        "mat_id":       d.get("mat_id"),
        "formula":      d.get("formula"),
        "elements":     json.dumps(d.get("elements", [])),
        "nsites":       d.get("nsites"),
        "spg":          d.get("spg"),
        "lambda_val":   tc.get("lambda"),
        "tc_max":       _extract_tc_max(tc),
        "imag":         1 if d.get("imag", True) else 0,
        "band_gap":     d.get("band_gap_ind"),
        "dos_ef":       d.get("dos_ef"),
        "e_above_hull": d.get("e_above_hull"),
        "e_form":       d.get("e_form"),
        "energy_total": d.get("energy_total"),
    }


def import_file(conn: sqlite3.Connection, filepath: str, filename: str) -> int:
    """将一个 JSON 文件的所有条目导入数据库"""
    with open(filepath) as f:
        data = json.load(f)

    entries = data.get("entries", [])
    if not entries:
        return 0

    rows = []
    idx_rows = []  # (element, entry_id)

    for raw in entries:
        d = raw.get("data", {})
        if not d:
            continue
        meta = _extract_meta(d)
        raw_json = json.dumps(d, ensure_ascii=False)

        rows.append((
            meta["mat_id"], filename, meta["formula"],
            meta["elements"], meta["nsites"], meta["spg"],
            meta["lambda_val"], meta["tc_max"], meta["imag"],
            meta["band_gap"], meta["dos_ef"],
            meta["e_above_hull"], meta["e_form"], meta["energy_total"],
            raw_json,
        ))

    # 批量插入 entries（分步，每步提交一次释放内存）
    BATCH = 500
    total = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        conn.executemany("""
            INSERT OR IGNORE INTO entries
                (mat_id, filename, formula, elements, nsites, spg,
                 lambda_val, tc_max, imag, band_gap, dos_ef,
                 e_above_hull, e_form, energy_total, data)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, batch)
        conn.commit()
        total += len(batch)

    return total


def build_element_index(conn: sqlite3.Connection):
    """从 entries 表扫描所有元素，构建 element_idx"""
    print("  构建元素索引...")
    t0 = time.time()
    cursor = conn.execute("SELECT id, elements FROM entries WHERE elements IS NOT NULL")
    idx_rows = []
    for row_id, elements_json in cursor:
        elements = json.loads(elements_json)
        for el in elements:
            idx_rows.append((el, row_id))

    conn.executemany(
        "INSERT OR IGNORE INTO element_idx (element, entry_id) VALUES (?, ?)",
        idx_rows
    )
    conn.commit()
    print(f"  元素索引完成: {len(idx_rows)} 条映射, 耗时 {time.time()-t0:.1f}s")


def import_all():
    """扫描所有 JSON 文件并导入数据库"""
    files = sorted([
        f for f in os.listdir(ALEXANDRIA_DIR)
        if f.startswith("alexandria_ph_") and f.endswith(".json")
    ])
    if not files:
        print("未找到 Alexandria 数据文件")
        return

    t_all = time.time()
    conn = get_conn()
    create_tables(conn)

    total_entries = 0
    for i, filename in enumerate(files):
        filepath = os.path.join(ALEXANDRIA_DIR, filename)
        t1 = time.time()
        n = import_file(conn, filepath, filename)
        total_entries += n
        elapsed = time.time() - t1
        print(f"  [{i+1}/{len(files)}] {filename}: {n} 条 ({elapsed:.1f}s)")

    print(f"\n全部导入完成: {total_entries} 条, 总耗时 {time.time()-t_all:.1f}s")

    build_element_index(conn)
    conn.close()

    # 输出数据库大小
    size = os.path.getsize(DB_PATH)
    print(f"\n数据库位置: {DB_PATH}")
    print(f"数据库大小: {size/1024/1024:.1f} MB")

    print("\n=== 元素行范围查询示例 ===")
    test_elements(conn=None)


def test_elements(conn=None):
    """查询每个元素的 min/max entry_id 行范围"""
    close = False
    if conn is None:
        conn = get_conn()
        close = True

    cursor = conn.execute("""
        SELECT element, MIN(entry_id) as min_id, MAX(entry_id) as max_id, COUNT(*) as cnt
        FROM element_idx
        GROUP BY element
        ORDER BY element
    """)
    print(f"{'元素':<6} {'起始行':>10} {'结束行':>10} {'条目数':>8}")
    print("-" * 40)
    for row in cursor:
        print(f"{row[0]:<6} {row[1]:>10} {row[2]:>10} {row[3]:>8}")

    if close:
        conn.close()


def _elements_match(entry_elements: set, query_elements: set, mode: str) -> bool:
    """判断条目元素是否匹配查询条件"""
    if not entry_elements:
        return False
    if mode == "only":
        return entry_elements == query_elements
    elif mode == "combination":
        return entry_elements.issubset(query_elements)
    elif mode == "contains":
        return query_elements.issubset(entry_elements)
    return False


def query_by_elements(elements: List[str], mode: str = "contains",
                      min_tc: float = None, stable_only: bool = False,
                      limit: int = 50, offset: int = 0) -> Dict:
    """按元素查询材料"""
    conn = get_read_conn()
    elements = sorted(set(elements))
    if not elements:
        return {"items": [], "total": 0}

    # 检查 element_idx 是否就绪
    has_index = conn.execute(
        "SELECT COUNT(*) FROM element_idx"
    ).fetchone()[0] > 0

    query_set = set(elements)

    # 构建基础查询 SQL（用子查询或 temp 表代替 Python 列表切片）
    # 先通过元素索引获取包含这些元素的 entry_id（放入临时表）
    conn.execute("DROP TABLE IF EXISTS _q")
    conn.execute("CREATE TEMP TABLE _q (entry_id INTEGER PRIMARY KEY)")
    n = len(elements)
    placeholders = ",".join("?" * n)

    if has_index:
        if mode == "contains":
            sub_sql = f"""
                INSERT INTO _q (entry_id)
                SELECT entry_id FROM element_idx
                WHERE element IN ({placeholders})
                GROUP BY entry_id HAVING COUNT(DISTINCT element) = ?
            """
            sub_params = elements + [n]
        elif mode == "combination":
            sub_sql = f"""
                INSERT INTO _q (entry_id)
                SELECT e.id FROM entries e
                WHERE (SELECT COUNT(*) FROM element_idx WHERE entry_id = e.id AND element IN ({placeholders})) = ?
                  AND (SELECT COUNT(*) FROM element_idx WHERE entry_id = e.id) <= ?
            """
            sub_params = elements + [n, n]
        elif mode == "only":
            sub_sql = f"""
                INSERT INTO _q (entry_id)
                SELECT e.id FROM entries e
                WHERE (SELECT COUNT(*) FROM element_idx WHERE entry_id = e.id AND element IN ({placeholders})) = ?
                  AND (SELECT COUNT(*) FROM element_idx WHERE entry_id = e.id) = ?
            """
            sub_params = elements + [n, n]
        else:
            return {"items": [], "total": 0}
    else:
        # 降级：扫描 elements 列
        conn.execute("""
            INSERT INTO _q (entry_id)
            SELECT id FROM entries WHERE elements IS NOT NULL
        """)
        # 后面用 Python 过滤
        sub_sql = None

    if sub_sql:
        conn.execute(sub_sql, sub_params)

    if not has_index:
        # 降级模式下用 Python 过滤 elements
        keep = set()
        for r in conn.execute("SELECT entry_id, elements FROM _q q JOIN entries e ON e.id = q.entry_id"):
            try:
                els = set(json.loads(r[1]))
            except Exception:
                continue
            if _elements_match(els, query_set, mode):
                keep.add(r[0])
        conn.execute("DELETE FROM _q")
        if keep:
            conn.executemany("INSERT INTO _q (entry_id) VALUES (?)", [(i,) for i in keep])

    # 对候选集过滤 tc、stable 等条件
    filters = []
    fp = []
    if min_tc is not None:
        filters.append("tc_max >= ?")
        fp.append(min_tc)
    if stable_only:
        filters.append("imag = 0")
    where_extra = (" AND " + " AND ".join(filters)) if filters else ""

    count_sql = f"""
        SELECT COUNT(*) FROM _q q
        JOIN entries e ON e.id = q.entry_id{where_extra}
    """
    total = conn.execute(count_sql, fp).fetchone()[0]

    data_sql = f"""
        SELECT e.id, e.mat_id, e.formula, e.elements, e.nsites, e.spg,
               e.lambda_val, e.tc_max, e.imag, e.band_gap, e.dos_ef
        FROM _q q JOIN entries e ON e.id = q.entry_id
        {where_extra}
        ORDER BY e.tc_max DESC NULLS LAST
        LIMIT ? OFFSET ?
    """
    params_data = fp + [limit, offset]

    items = []
    for r in conn.execute(data_sql, params_data).fetchall():
        items.append({
            "id": r[0], "mat_id": r[1], "formula": r[2],
            "elements": json.loads(r[3]) if r[3] else [],
            "nsites": r[4], "spg": r[5],
            "lambda_val": r[6], "tc_max": r[7], "imag": bool(r[8]),
            "band_gap": r[9], "dos_ef": r[10],
        })

    conn.execute("DROP TABLE IF EXISTS _q")
    return {
        "items": items,
        "total": total,
        "has_prev": offset > 0,
        "has_next": offset + limit < total,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        # 测试查询
        result = query_by_elements(
            sys.argv[2].split(",") if len(sys.argv) > 2 else ["H", "Mo", "Nb"],
            mode=sys.argv[3] if len(sys.argv) > 3 else "contains",
            limit=5,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "ranges":
        test_elements()
    else:
        import_all()
