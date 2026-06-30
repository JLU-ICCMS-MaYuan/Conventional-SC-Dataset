#!/usr/bin/env python3
"""将 ../综述 目录下的综述 Markdown 文件分块并嵌入到 Chroma review_chunks 集合。

用法:
    cd /home/work/workshop/git/SC-Wiki
    EMBEDDING_API_KEY="sk-xxx" EMBEDDING_BASE_URL="https://xxx/v1" python backend/rag/ingest/ingest_reviews.py
"""

from __future__ import annotations

import sys
import time as _time
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.rag.config import settings
from backend.rag.ingest.chunker import chunk_paper
from backend.rag.ingest.embedder import embed_texts
from backend.rag.vectordb import (
    add_chunks,
    collection_stats,
    REVIEW_COLLECTION_NAME,
    COLLECTION_NAME,
    _get_client,
)

REVIEW_DIR = _project_root / "综述"
REVIEW_START_PAPER_ID = 900000


def find_review_mds(root: Path) -> list[tuple[Path, int]]:
    jobs = []
    for paper_dir in sorted(root.iterdir()):
        if not paper_dir.is_dir():
            continue
        auto_dir = paper_dir / "auto"
        if not auto_dir.exists():
            continue
        mds = sorted(auto_dir.glob("*.md"))
        paper_id = hash(paper_dir.name) % 100000 + REVIEW_START_PAPER_ID
        for md in mds:
            jobs.append((md, paper_id))
    return jobs


def main() -> None:
    if not REVIEW_DIR.exists():
        print(f"错误：综述目录不存在 {REVIEW_DIR}")
        sys.exit(1)

    jobs = find_review_mds(REVIEW_DIR)
    print(f"找到 {len(jobs)} 个综述 Markdown 文件")
    print(f"Embedding: {settings.embedding_model} @ {settings.embedding_url[:40]}...")
    print(f"Chroma: {settings.chroma_path}")

    # 收集 chunks
    all_chunks = []
    for md_path, paper_id in jobs:
        try:
            text = md_path.read_text(encoding="utf-8", errors="ignore")
            if len(text) < 200:
                continue
            chunks = chunk_paper(text, paper_id=paper_id, max_tokens=800)
            print(f"  {md_path.parent.parent.name}/{md_path.name} → {len(chunks)} chunks")
            for c in chunks:
                all_chunks.append({
                    "id": f"review_{c.paper_id}_{c.chunk_index}",
                    "paper_id": c.paper_id,
                    "chunk_index": c.chunk_index,
                    "section_name": c.section_name or "",
                    "content": c.content,
                })
        except Exception as e:
            print(f"  失败: {md_path} - {e}")

    if not all_chunks:
        print("无可用 chunks。")
        return
    print(f"\n总计 {len(all_chunks)} chunks，开始向量化...")

    # 清空旧数据
    client = _get_client()
    try:
        client.delete_collection(REVIEW_COLLECTION_NAME)
    except Exception:
        pass

    # 小批次 + 长间隔，避免限流
    batch_size = 10
    indexed = 0
    total = len(all_chunks)
    err_count = 0

    for i in range(0, total, batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]

        for attempt in range(15):
            try:
                embeddings = embed_texts(texts)
                add_chunks(batch, embeddings, collection=REVIEW_COLLECTION_NAME)
                indexed += len(batch)
                err_count = 0
                print(f"  {indexed}/{total}")
                break
            except Exception as e:
                err = str(e)[:200]
                if "429" in err:
                    err_count += 1
                    wait = min(attempt * 10 + 10, 120)
                    print(f"  限流(#{err_count}), 等待 {wait}s...")
                    _time.sleep(wait)
                else:
                    print(f"  失败 batch {i}: {err}")
                    sys.exit(1)
        _time.sleep(3)

    # 统计
    ms = collection_stats(COLLECTION_NAME)
    rs = collection_stats(REVIEW_COLLECTION_NAME)
    print(f"\n完成！paper_chunks={ms['count']}  review_chunks={rs['count']}")


if __name__ == "__main__":
    main()
