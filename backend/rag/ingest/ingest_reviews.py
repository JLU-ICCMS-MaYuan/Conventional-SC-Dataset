#!/usr/bin/env python3
"""将 ../综述 目录下的综述 Markdown 文件分块并嵌入到 Chroma review_chunks 集合。

用法:
    cd /home/work/workshop/git/SC-Wiki
    python backend/rag/ingest/ingest_reviews.py

不依赖 SQLite —— 直接用 folder index 作为 paper_id（900000+），
chunks 可被检索但暂时没有 Paper 元信息（title/doi）。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保 backend.rag 在 sys.path
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
)

REVIEW_DIR = _project_root / "综述"
REVIEW_START_PAPER_ID = 900000  # 避免与现有 paper_id 冲突


def find_review_mds(root: Path) -> list[tuple[Path, int]]:
    """找到所有综述 markdown 文件，返回 (path, paper_id)。"""
    jobs = []
    for paper_dir in sorted(root.iterdir()):
        if not paper_dir.is_dir():
            continue
        auto_dir = paper_dir / "auto"
        if not auto_dir.exists():
            continue
        mds = sorted(auto_dir.glob("*.md"))
        if not mds:
            continue
        # 用目录字母序作为 paper_id
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
    print(f"Embedding 模型: {settings.embedding_model}")
    print(f"Chroma 路径: {settings.chroma_path}")

    # 收集所有 chunks
    all_chunks = []
    for md_path, paper_id in jobs:
        try:
            text = md_path.read_text(encoding="utf-8", errors="ignore")
            if len(text) < 200:
                print(f"  跳过（太短）: {md_path.name}")
                continue
            chunks = chunk_paper(text, paper_id=paper_id, max_tokens=800)
            print(f"  {md_path.parent.parent.name}/{md_path.name} → {len(chunks)} chunks [paper_id={paper_id}]")
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
        print("没有可用的 chunks。")
        return

    print(f"\n总计 {len(all_chunks)} chunks，开始向量化...")

    # 批量 embedding（每次 50 个）
    batch_size = 50
    indexed = 0
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        try:
            embeddings = embed_texts(texts)
            add_chunks(batch, embeddings, collection=REVIEW_COLLECTION_NAME)
            indexed += len(batch)
            print(f"  已索引: {indexed}/{len(all_chunks)}")
        except Exception as e:
            print(f"  Embedding 失败 batch {i}: {e}")
            print("  请确认 OPENAI_API_KEY 已设置。")
            sys.exit(1)

    # 统计
    main_stats = collection_stats(COLLECTION_NAME)
    review_stats = collection_stats(REVIEW_COLLECTION_NAME)
    print(f"\n完成！")
    print(f"  paper_chunks: {main_stats['count']} chunks")
    print(f"  review_chunks: {review_stats['count']} chunks")


if __name__ == "__main__":
    main()
