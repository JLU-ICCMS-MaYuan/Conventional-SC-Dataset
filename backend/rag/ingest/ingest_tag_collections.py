#!/usr/bin/env python3
"""在 15 个文件夹集合之上建 6 个合并标签集合（纯本地复制向量）。

用法:
    cd /home/work/workshop/git/SC-Wiki
    python backend/rag/ingest/ingest_tag_collections.py
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.rag.vectordb import (
    get_chunks,
    add_chunks,
    collection_stats,
    COLLECTION_NAME,
    _get_client,
)

# 文件夹 → 标签
FOLDER_TO_TAG: dict[str, str] = {
    "理论-三元": "theoretical",
    "理论-二元": "theoretical",
    "理论-四元": "theoretical",
    "理论-五元": "theoretical",
    "理论-六元": "theoretical",
    "固体氢": "solid_hydrogen",
    "氢化物超导机理研究": "mechanism",
    "氢化物非谐研究": "mechanism",
    "分子动力学研究": "mechanism",
    "机器学习领域应用": "ml",
    "实验-二元": "experimental",
    "实验-三元": "experimental",
    "实验-四元": "experimental",
    "综述": "review",
}

DB_PATH = _project_root / "data" / "dev.db"


def main() -> None:
    # 1. 按标签分组 paper_id
    tag_to_pids: dict[str, list[int]] = defaultdict(list)
    tag_to_source_colls: dict[str, set[str]] = defaultdict(set)

    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("SELECT id, source_file_path FROM papers").fetchall()
    for pid, path in rows:
        if not path:
            continue
        folder = path.split("/")[0]
        tag = FOLDER_TO_TAG.get(folder)
        if tag:
            tag_to_pids[tag].append(pid)

    conn.close()

    # 收集每个标签对应的源集合
    for folder, tag in FOLDER_TO_TAG.items():
        tag_to_source_colls[tag].add(f"{folder}_chunks")

    print("标签 → 文件夹集合 → paper数:")
    for tag in sorted(tag_to_pids):
        pids = tag_to_pids[tag]
        srcs = tag_to_source_colls[tag]
        print(f"  {tag}: {len(pids)} 篇 ← {srcs}")

    # 2. 删除旧标签集合
    client = _get_client()
    existing = {c.name for c in client.list_collections()}
    for tag in tag_to_pids:
        name = f"{tag}_chunks"
        if name in existing:
            client.delete_collection(name)
            print(f"已删除: {name}")

    # 3. 逐 paper 复制到标签集合
    total = 0
    for tag, pids in sorted(tag_to_pids.items()):
        tag_name = f"{tag}_chunks"
        copied = 0

        for pid in pids:
            result = get_chunks(
                where={"paper_id": str(pid)},
                include_embeddings=True,
                collection=COLLECTION_NAME,
            )
            ids = result.get("ids", [])
            if not ids:
                continue

            chunks = []
            for i in range(len(ids)):
                m = result["metadatas"][i]
                chunks.append({
                    "id": f"tag_{tag}_{ids[i]}",
                    "paper_id": int(m["paper_id"]),
                    "chunk_index": m["chunk_index"],
                    "section_name": m.get("section_name", ""),
                    "content": result["documents"][i],
                })

            add_chunks(chunks, result["embeddings"], collection=tag_name)
            copied += len(chunks)

        print(f"  {tag}_chunks: {copied} chunks ({len(pids)} 篇)")
        total += copied

    # 4. 验证
    print(f"\n== 验证 ==")
    for tag in sorted(tag_to_pids):
        try:
            cs = collection_stats(f"{tag}_chunks")
            print(f"  {tag}_chunks: {cs['count']}")
        except Exception:
            print(f"  {tag}_chunks: (空)")
    print(f"  总计标签 chunks: {total}")


if __name__ == "__main__":
    main()
