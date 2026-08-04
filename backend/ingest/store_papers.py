"""
store_papers.py — 数据库写入模块（v2 精简版）。

论文元信息写入 papers 表。物性表 key_properties 由 enrich_papers → ingest_properties 管线负责
（LLM 二次富化后写入，质量更高），不再从 extractor 的 data_points 直写。
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Paper
from backend.ingest.extractor import ExtractionResult


async def store_extraction(
    result: ExtractionResult,
    source_file_path: str,
    session: AsyncSession,
    uploaded_by_user_id: int | None = None,
) -> int | None:
    """存储提取结果到数据库。

    论文元信息（title / summary / keywords / paper_type）写入 papers 表，
    支持按 DOI 或 source_file_path 判重更新。

    Returns:
        新论文或更新论文的 id；无有效数据时返回 None。
    """
    paper_data = result.paper

    # ── 判重 ────────────────────────────────────────────────────────
    doi = (paper_data.get("doi") or "").strip() or None
    if doi:
        r = await session.execute(
            select(Paper).where(Paper.doi == doi)
        )
        existing = r.scalar_one_or_none()
        if existing:
            # 已存在且已审核 → 跳过
            if existing.review_status == "approved":
                print(f"  [存储] 跳过已审核论文 doi={doi}")
                return existing.id
            # 待审核 → 更新
            existing.title = paper_data.get("title")
            existing.authors = paper_data.get("authors") or None
            existing.journal = paper_data.get("journal")
            existing.year = paper_data.get("year")
            existing.abstract = paper_data.get("abstract")
            existing.summary = result.summary
            existing.keywords_tags = json.dumps(result.keywords_tags, ensure_ascii=False) if result.keywords_tags else None
            existing.paper_type = result.paper_type
            await session.commit()
            print(f"  [存储] 更新待审核 Paper id={existing.id} doi={doi}")
            return existing.id

    # 按 source_file_path 查重
    r = await session.execute(
        select(Paper).where(Paper.source_file_path == source_file_path)
    )
    existing = r.scalar_one_or_none()
    if existing:
        if existing.review_status == "approved":
            print(f"  [存储] 跳过已审核论文 path={source_file_path}")
            return existing.id
        existing.title = paper_data.get("title")
        existing.authors = paper_data.get("authors") or None
        existing.journal = paper_data.get("journal")
        existing.year = paper_data.get("year")
        existing.abstract = paper_data.get("abstract")
        existing.summary = result.summary
        existing.keywords_tags = json.dumps(result.keywords_tags, ensure_ascii=False) if result.keywords_tags else None
        existing.paper_type = result.paper_type
        await session.commit()
        print(f"  [存储] 更新待审核 Paper id={existing.id} path={source_file_path}")
        return existing.id

    # ── 新建 ────────────────────────────────────────────────────────
    paper = Paper(
        doi=doi,
        review_status="pending" if re.match(r"^upload/", source_file_path) else "approved",
        title=paper_data.get("title"),
        authors=paper_data.get("authors") or None,
        journal=paper_data.get("journal"),
        year=paper_data.get("year"),
        abstract=paper_data.get("abstract"),
        summary=result.summary,
        keywords_tags=json.dumps(result.keywords_tags, ensure_ascii=False) if result.keywords_tags else None,
        source_file_path=source_file_path,
        paper_type=result.paper_type,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    session.add(paper)
    await session.flush()
    paper_id = paper.id
    print(f"  [存储] 新建 Paper id={paper_id}")

    await session.commit()
    print(f"  [存储] 论文元信息入库完成（物性由 enrich_papers → ingest_properties 管线后续写入）")
    return paper_id

# ═══════════════════════════════════════════════════════════════════
# 以下来自 ingest_properties.py — clean_results JSON → key_properties 增量写入
# ═══════════════════════════════════════════════════════════════════

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text as sqla_text

from backend.database import DATABASE_URL
from backend.ingest.prop_names import normalize_prop_name
from backend.scripts.rebuild_from_clean_results import (
    extract_cond_number,
    infer_sc_type,
    normalize_formula,
    paper_is_experimental,
    parse_formula,
    parse_range,
)

CLEAN_DIR = Path(__file__).resolve().parents[1] / "data" / "clean_results"


def ingest_paper(paper_id: int, data: dict, engine=None) -> int:
    """将单篇 clean_results JSON 的全部物性写入 key_properties（幂等）。返回写入行数。"""
    if engine is None:
        engine = create_engine(DATABASE_URL)
    kp = data.get("key_properties")
    if isinstance(kp, list):
        rms = data.get("research_materials") or []
        kp = {rms[0]: kp} if len(rms) == 1 and isinstance(rms[0], str) else {}
    if not isinstance(kp, dict):
        return 0

    is_exp = paper_is_experimental(data.get("paper_type"))
    sc_cache: dict[str, int] = {}
    count = 0

    for material, props in kp.items():
        if not isinstance(props, list):
            continue
        material = material.strip()[:255]
        elements = parse_formula(material)
        sc_id = None
        if elements:
            system_key = "-".join(sorted(elements))
            formula_norm = normalize_formula(elements)
            cache_key = formula_norm
            if cache_key in sc_cache:
                sc_id = sc_cache[cache_key]
            else:
                with engine.connect() as c:
                    row = c.execute(sqla_text(
                        "SELECT id FROM chemical_systems WHERE system_key = :k"
                    ), {"k": system_key}).fetchone()
                    if row:
                        cs_id = row[0]
                    else:
                        c.execute(sqla_text(
                            "INSERT INTO chemical_systems (system_key, elements_list, element_count, created_at, updated_at) "
                            "VALUES (:k, :e, :n, NOW(), NOW())"
                        ), {"k": system_key, "e": json.dumps(sorted(elements)), "n": len(elements)})
                        cs_id = c.execute(sqla_text("SELECT LAST_INSERT_ID()")).scalar()
                    row = c.execute(sqla_text(
                        "SELECT id FROM superconductors WHERE formula_normalized = :fn"
                    ), {"fn": formula_norm}).fetchone()
                    if row:
                        sc_id = row[0]
                    else:
                        total = sum(elements.values()) or 1.0
                        ratio = {k: round(v / total, 6) for k, v in elements.items()}
                        c.execute(sqla_text("""
                            INSERT INTO superconductors
                                (chemical_system_id, chemical_formula, formula_normalized, display_name,
                                 elements_list, composition, element_ratio, created_at, updated_at)
                            VALUES (:cs, :f, :fn, :f, :el, :comp, :ratio, NOW(), NOW())
                        """), {"cs": cs_id, "f": material, "fn": formula_norm,
                               "el": json.dumps(sorted(elements)), "comp": json.dumps(elements),
                               "ratio": json.dumps(ratio)})
                        sc_id = c.execute(sqla_text("SELECT LAST_INSERT_ID()")).scalar()
                    c.commit()
                sc_cache[cache_key] = sc_id

        max_p = max(
            (extract_cond_number(p.get("condition"), "pressure") or 0)
            for p in props if isinstance(p, dict)
        ) if any(isinstance(p, dict) for p in props) else None
        sc_type = infer_sc_type(elements, max_p) if elements else None

        with engine.connect() as c:
            c.execute(sqla_text(
                "DELETE FROM key_properties WHERE paper_id = :pid AND source_label = 'clean_results' AND material = :mat"
            ), {"pid": paper_id, "mat": material})
            c.commit()

        rows = []
        for p in props:
            if not isinstance(p, dict):
                continue
            name_raw = str(p.get("name") or "").strip()[:255]
            if not name_raw:
                continue
            name, matched = normalize_prop_name(name_raw)
            if not matched:
                from backend.ingest.prop_names import ai_normalize
                name = ai_normalize(name_raw)
            vmin, vmax, vraw = parse_range(p.get("value"))
            cond = p.get("condition") if isinstance(p.get("condition"), dict) else None
            rows.append({
                "pid": paper_id, "sid": sc_id, "mat": material,
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
            count += 1

        if rows:
            with engine.connect() as c:
                c.execute(sqla_text("""
                    INSERT INTO key_properties
                        (paper_id, superconductor_id, material, name, name_raw, name_note,
                         value_min, value_max, value_raw, unit, pressure_gpa, temperature_k,
                         condition_json, condition_note, is_primary, superconductor_type,
                         article_type, source_label, created_at, updated_at)
                    VALUES (:pid, :sid, :mat, :name, :nraw, :nnote,
                            :vmin, :vmax, :vraw, :unit, :pg, :tk,
                            :cj, :cnote, :prim, :st, :at, 'clean_results', NOW(), NOW())
                """), rows)
                c.commit()

    return count


def _cli_ingest():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-id", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--since", type=int, default=0)
    args = ap.parse_args()

    engine = create_engine(DATABASE_URL)

    if args.paper_id:
        f = CLEAN_DIR / f"{args.paper_id}.json"
        if not f.exists():
            print(f"文件不存在: {f}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(f.read_text())
        n = ingest_paper(args.paper_id, data, engine)
        materials = list(data.get("key_properties", {}).keys()) if isinstance(data.get("key_properties"), dict) else []
        print(f"paper_id={args.paper_id} 写入 {n} 条物性，材料: {materials}")
    elif args.all:
        total = 0
        for f in sorted(CLEAN_DIR.glob("*.json")):
            if not f.stem.isdigit():
                continue
            pid = int(f.stem)
            if pid < args.since:
                continue
            data = json.loads(f.read_text())
            n = ingest_paper(pid, data, engine)
            if n:
                total += n
                print(f"  paper_id={pid}: {n} 条")
        print(f"\n全量增量写入: {total} 条")
    else:
        print("请指定 --paper-id N 或 --all", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_ingest()


# ═══════════════════════════════════════════════════════════════════
# chunk + embed：论文全文 → RAG 向量索引
# ═══════════════════════════════════════════════════════════════════

def chunk_and_embed(markdown_text: str, paper_id: int) -> int:
    """将论文全文切块→向量化→写入 Chroma。返回索引的 chunk 数。"""
    from backend.ingest.chunker import chunk_paper
    from backend.ingest.embedder import embed_texts, index_chunks

    chunks = chunk_paper(markdown_text, paper_id)
    if not chunks:
        print(f"  [RAG] paper_id={paper_id}: 无有效文本块，跳过向量化")
        return 0

    chunk_dicts = [
        {"id": f"paper_{paper_id}_chunk_{c.chunk_index}",
         "paper_id": c.paper_id, "chunk_index": c.chunk_index,
         "section_name": c.section_name or "", "content": c.content}
        for c in chunks
    ]
    texts = [c.content for c in chunks]
    embeddings = embed_texts(texts)
    ids = index_chunks(chunk_dicts, embeddings)
    print(f"  [RAG] paper_id={paper_id}: {len(ids)} chunks 已索引")
    return len(ids)
