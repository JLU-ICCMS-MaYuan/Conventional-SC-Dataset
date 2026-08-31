"""
知识图谱同步 v2: MySQL → Neo4j
用法: python backend/ingest/sync_neo4j.py [--clear] [--workers N]
"""
import json, os, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from sqlalchemy import text

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

DEFAULT_WORKERS = 4

# Paper 节点字段映射: MySQL column → Neo4j property
PAPER_FIELDS = [
    "id", "doi", "title", "year", "journal", "volume", "pages",
    "abstract", "authors", "summary", "paper_type", "keywords_tags",
    "methodology", "key_finding", "research_motivation",
    "research_materials", "referenced_materials",
    "material_relations", "builds_on",
]


def _batches(items, n):
    size = max(1, len(items) // n)
    return [items[i:i + size] for i in range(0, len(items), size)]


class KGSync:
    def __init__(self, workers=DEFAULT_WORKERS):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.workers = workers

    def close(self):
        self.driver.close()

    def sync_single(self, paper_id: int) -> int:
        """审批通过后增量同步单篇论文到 Neo4j。返回创建的节点/关系数。"""
        from backend.database import SessionLocal
        db = SessionLocal()
        paper = db.execute(text(
            "SELECT id, doi, title, year, journal, volume, pages, abstract, authors, summary, paper_type, "
            "keywords_tags, methodology, key_finding, research_motivation FROM papers WHERE id = :pid"
        ), {"pid": paper_id}).fetchone()
        db.close()
        if not paper:
            return 0

        pid = paper[0]
        field_names = ["id", "doi", "title", "year", "journal", "volume", "pages", "abstract", "authors", "summary", "paper_type", "keywords_tags", "methodology", "key_finding", "research_motivation"]
        props = {field_names[i]: paper[i] for i in range(len(paper)) if paper[i] is not None}

        authors = props.get("authors")
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = []
        props["author_list"] = json.dumps(authors, ensure_ascii=False) if authors else "[]"

        with self.driver.session() as s:
            s.run("MERGE (p:Paper {paper_id: $id}) SET p += $props", id=pid, props=props)

        # Materials from key_properties
        from backend.database import SessionLocal as SL
        db2 = SL()
        kps = db2.execute(text(
            "SELECT DISTINCT material, superconductor_type, pressure_gpa, structure_text, structure_format "
            "FROM key_properties WHERE paper_id = :pid AND is_primary = 1"
        ), {"pid": pid}).fetchall()
        db2.close()

        with self.driver.session() as s:
            for mat, sc_type, pressure, stxt, sfmt in kps:
                s.run("MERGE (m:Material {formula: $f}) SET m.sc_type = $sc, m.pressure_gpa = $p, "
                      "m.structure_text = $stxt, m.structure_format = $sfmt",
                      f=mat, sc=sc_type, p=pressure, stxt=stxt, sfmt=sfmt)
                s.run("MATCH (p:Paper {paper_id: $pid}) MATCH (m:Material {formula: $f}) MERGE (p)-[:STUDIES]->(m)",
                      pid=pid, f=mat)

        return 1

    # ═══════════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════════

    def clear_and_constrain(self):
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
            for cypher in [
                "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
                "CREATE CONSTRAINT material_f IF NOT EXISTS FOR (m:Material) REQUIRE m.formula IS UNIQUE",
                "CREATE CONSTRAINT researcher_n IF NOT EXISTS FOR (r:Researcher) REQUIRE r.name IS UNIQUE",
            ]:
                try:
                    s.run(cypher)
                except Exception:
                    pass
        print("已清空 + 创建约束")

    # ═══════════════════════════════════════════════
    # Paper 节点 (MySQL + clean_results)
    # ═══════════════════════════════════════════════

    def sync_papers(self):
        from backend.database import SessionLocal
        db = SessionLocal()
        rows = db.execute(text(
            "SELECT " + ", ".join(PAPER_FIELDS) + " FROM papers"
        )).fetchall()
        db.close()

        cols = [c[0] for c in rows[0]._mapping.items()] if rows else PAPER_FIELDS
        total = len(rows)

        def _batch_sync(batch):
            with self.driver.session() as s:
                for row in batch:
                    d = dict(zip(cols, row))
                    pid = d["id"]
                    props = {k: d.get(k) for k in PAPER_FIELDS if d.get(k)}

                    # 处理 authors JSON
                    authors = d.get("authors")
                    if isinstance(authors, str):
                        try:
                            authors = json.loads(authors)
                        except Exception:
                            authors = []
                    props["author_list"] = json.dumps(authors, ensure_ascii=False) if authors else "[]"

                    s.run("""
                        MERGE (p:Paper {paper_id: $id})
                        SET p += $props
                    """, id=pid, props=props)

        batches = _batches([tuple(r) for r in rows], self.workers)
        with ThreadPoolExecutor(self.workers) as ex:
            list(ex.map(_batch_sync, batches))
        print(f"Paper: {total} 节点")

    # ═══════════════════════════════════════════════
    # Material + Property (MySQL)
    # ═══════════════════════════════════════════════

    def sync_materials(self):
        from backend.database import SessionLocal
        from backend.models import Superconductor, KeyProperty
        db = SessionLocal()
        mats = db.query(Superconductor).all()
        # 查询每个 material 的结构信息
        kp_rows = db.query(
            KeyProperty.material, KeyProperty.structure_text, KeyProperty.structure_format
        ).filter(
            KeyProperty.structure_text.isnot(None),
            KeyProperty.superconductor_id.isnot(None),
        ).all()
        # 取每个 material 第一条结构
        struct_map: dict[str, tuple[str, str]] = {}
        for mat, txt, fmt in kp_rows:
            if mat not in struct_map:
                struct_map[mat] = (txt, fmt or "cif")
        db.close()

        def _batch_sync(batch):
            with self.driver.session() as s:
                for m in batch:
                    st = struct_map.get(m.chemical_formula)
                    s.run("""
                        MERGE (mat:Material {formula: $f})
                        SET mat.chemical_formula = $f,
                            mat.elements = $elem,
                            mat.structure_text = $stxt,
                            mat.structure_format = $sfmt
                    """, f=m.chemical_formula, elem=m.elements_list,
                         stxt=st[0] if st else None,
                         sfmt=st[1] if st else None)

        batches = _batches(mats, self.workers)
        with ThreadPoolExecutor(self.workers) as ex:
            list(ex.map(_batch_sync, batches))
        print(f"Material: {len(mats)} 节点, 含结构: {len(struct_map)}")

    def sync_properties(self):
        from backend.database import SessionLocal
        db = SessionLocal()
        rows = db.execute(text("""
            SELECT kp.value_max AS tc, kp.pressure_gpa, kp.material AS formula
            FROM key_properties kp
            WHERE kp.name = 'critical_temperature'
              AND kp.value_max IS NOT NULL
              AND kp.is_primary = 1
        """)).fetchall()
        db.close()

        def _batch_sync(batch):
            with self.driver.session() as s:
                for tc, p, formula in batch:
                    if not tc:
                        continue
                    s.run("""
                        MATCH (m:Material {formula: $f})
                        MERGE (m)-[:HAS_PROPERTY]->(prop:Property {
                            name: $name, value: $val, unit: $unit
                        })
                        SET prop.pressure_gpa = $p
                    """, f=formula, name="Tc", val=float(tc),
                         unit="K", p=p)

        batches = _batches(rows, self.workers)
        with ThreadPoolExecutor(self.workers) as ex:
            list(ex.map(_batch_sync, batches))
        print(f"Property: {len(rows)} 个 (is_primary critical_temperature)")

    # ═══════════════════════════════════════════════
    # Researcher (从 authors JSON)
    # ═══════════════════════════════════════════════

    def sync_researchers(self):
        with self.driver.session() as s:
            # 从 Paper.author_list 提取
            result = s.run("MATCH (p:Paper) WHERE p.author_list IS NOT NULL RETURN p.paper_id, p.author_list")
            author_pairs = defaultdict(list)
            for r in result:
                try:
                    raw = r["p.author_list"]
                    authors = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    continue
                for a in authors:
                    name = a.get("name", "").strip() if isinstance(a, dict) else str(a).strip()
                    if name and len(name) > 1:
                        author_pairs[name].append(r.get("p.paper_id") or r.get("paper_id"))

            for name, pids in author_pairs.items():
                s.run("MERGE (r:Researcher {name: $name})", name=name)
                for pid in pids:
                    s.run("""
                        MATCH (r:Researcher {name: $name})
                        MATCH (p:Paper {paper_id: $pid})
                        MERGE (r)-[:AUTHORED]->(p)
                    """, name=name, pid=pid)

        print(f"Researcher: {len(author_pairs)} 人 + AUTHORED 关系")

    # ═══════════════════════════════════════════════
    # 关系: STUDIES (Paper → Material)
    # ═══════════════════════════════════════════════

    def sync_studies(self):
        with self.driver.session() as s:
            result = s.run(
                "MATCH (p:Paper) WHERE p.material_relations IS NOT NULL RETURN p.paper_id, p.material_relations"
            )
            count = 0
            for r in result:
                raw = r.get("p.material_relations") or r.get("material_relations")
                if not raw: continue
                try:
                    rels = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    continue
                if not rels: continue
                for rel in rels:
                    if isinstance(rel, str): rel = {"material": rel, "relation": "investigates"}
                    mat = rel.get("material", "")
                    role = rel.get("relation", "investigates")
                    evidence = rel.get("evidence", "")[:500]
                    if not mat:
                        continue
                    s.run("""
                        MATCH (p:Paper {paper_id: $pid})
                        MERGE (m:Material {formula: $mat})
                        MERGE (p)-[:STUDIES {role: $role, evidence: $ev}]->(m)
                    """, pid=r.get("p.paper_id") or r.get("paper_id"), mat=mat, role=role, ev=evidence)
                    count += 1
        print(f"STUDIES: {count} 条")

    # ═══════════════════════════════════════════════
    # 关系: BUILDS_ON (Paper → Paper)
    # ═══════════════════════════════════════════════

    def sync_builds_on(self):
        with self.driver.session() as s:
            result = s.run(
                "MATCH (p:Paper) WHERE p.builds_on IS NOT NULL RETURN p.paper_id, p.builds_on"
            )
            count = 0
            for r in result:
                raw = r.get("p.builds_on") or r.get("builds_on")
                if not raw: continue
                try:
                    builds = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    continue
                if not builds: continue
                for b in builds:
                    if isinstance(b, str): b = {"work": b, "hint": ""}
                    work = b.get("work", "")
                    hint = b.get("hint", "")
                    s.run("""
                        MATCH (p:Paper {paper_id: $pid})
                        MERGE (target:Paper {paper_id: -1})
                        SET target.work_name = $work, target.work_hint = $hint
                        MERGE (p)-[:BUILDS_ON {work: $work}]->(target)
                    """, pid=r.get("p.paper_id") or r.get("paper_id"), work=work, hint=hint)
                    # 后面会通过 work_hint 模糊匹配真实 paper_id
                    count += 1
        print(f"BUILDS_ON: {count} 条 (待后续匹配真实paper_id)")

    # ═══════════════════════════════════════════════
    # SHARES_STRUCTURE (Material → Material)
    # ═══════════════════════════════════════════════

    def sync_shares_structure(self):
        with self.driver.session() as s:
            result = s.run("""
                MATCH (m1:Material) WHERE m1.space_group IS NOT NULL
                MATCH (m2:Material) WHERE m2.space_group IS NOT NULL AND m2.formula < m1.formula
                AND m1.space_group = m2.space_group AND m1.crystal_structure = m2.crystal_structure
                MERGE (m1)-[:SHARES_STRUCTURE]->(m2)
                RETURN count(*) AS c
            """)
            cnt = result.single()["c"]
        print(f"SHARES_STRUCTURE: {cnt} 条")

    # ═══════════════════════════════════════════════

    def run(self):
        t0 = time.time()
        if "--clear" in sys.argv:
            self.clear_and_constrain()
        self.sync_papers()
        self.sync_materials()
        self.sync_properties()
        self.sync_researchers()
        self.sync_studies()
        self.sync_builds_on()
        self.sync_shares_structure()
        print(f"\n完成! 耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    workers = DEFAULT_WORKERS
    for i, a in enumerate(sys.argv):
        if a == "--workers" and i + 1 < len(sys.argv):
            workers = int(sys.argv[i + 1])
    KGSync(workers).run()
