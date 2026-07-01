#!/usr/bin/env python3
"""按 source_file_path 文件夹拆分 paper_chunks 到独立 ChromaDB 集合。

用法:
    cd /home/work/workshop/git/SC-Wiki
    python backend/rag/ingest/ingest_split_collections.py

纯本地复制向量，无需 API key。从 paper_chunks 复制 embedding 到各文件夹集合。
"""

from __future__ import annotations

import sys
import sqlite3
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
    _get_collection,
)

# 文件夹名 → ChromaDB 集合名（安全的英文名）
FOLDER_COLLECTION_MAP = {
    "理论-三元": "theoretical_ternary",
    "理论-二元": "theoretical_binary",
    "理论-四元": "theoretical_quaternary",
    "理论-五元": "theoretical_quinary",
    "理论-六元": "theoretical_senary",
    "固体氢": "solid_hydrogen",
    "氢化物超导机理研究": "mechanism",
    "氢化物非谐研究": "anharmonic",
    "分子动力学研究": "molecular_dynamics",
    "机器学习领域应用": "machine_learning",
    "实验-二元": "experimental_binary",
    "实验-三元": "experimental_ternary",
    "实验-四元": "experimental_quaternary",
    "综述": "review",
    "upload": "upload",
}

DB_PATH = _project_root / "data" / "dev.db"


def main() -> None:
    # 1. 按文件夹分组 paper_id
    papers_by_folder: dict[str, list[int]] = defaultdict(list)
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("SELECT id, source_file_path FROM papers").fetchall()
    for pid, path in rows:
        if path:
            folder = path.split("/")[0]  # 一级目录
            papers_by_folder[folder].append(pid)
        else:
            papers_by_folder["unknown"].append(pid)
    conn.close()

    print(f"数据库: {DB_PATH}")
    print(f"文件夹数: {len(papers_by_folder)}")
    for folder, pids in sorted(papers_by_folder.items()):
        coll = FOLDER_COLLECTION_MAP.get(folder, folder)
        print(f"  {folder} → {coll}_chunks ({len(pids)} 篇)")

    # 2. 删除旧的文件夹集合（保留 paper_chunks）
    client = _get_client()
    existing = {c.name for c in client.list_collections()}
    for folder in FOLDER_COLLECTION_MAP.values():
        name = f"{folder}_chunks"
        if name in existing:
            client.delete_collection(name)
            print(f"  已删除旧集合: {name}")

    # 3. 逐文件夹复制
    total_copied = 0
    for folder, pids in sorted(papers_by_folder.items()):
        coll_name = FOLDER_COLLECTION_MAP.get(folder, folder) + "_chunks"
        print(f"\n复制 {folder} ({len(pids)} 篇) → {coll_name}")

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

            embeddings = result["embeddings"]
            documents = result["documents"]
            metadatas = result["metadatas"]

            # 构造 chunks，id 加上前缀避免跨集合冲突
            chunks = []
            for i in range(len(ids)):
                chunks.append({
                    "id": f"{folder}_{ids[i]}",
                    "paper_id": int(metadatas[i]["paper_id"]),
                    "chunk_index": metadatas[i]["chunk_index"],
                    "section_name": metadatas[i].get("section_name", ""),
                    "content": documents[i],
                })

            add_chunks(chunks, embeddings, collection=coll_name)
            copied += len(chunks)

        print(f"  {copied} chunks 已复制")
        total_copied += copied

    # 4. 验证
    print(f"\n== 验证 ==")
    ms = collection_stats(COLLECTION_NAME)
    print(f"  paper_chunks: {ms['count']}")
    grand = ms["count"]
    for folder, coll in sorted(FOLDER_COLLECTION_MAP.items()):
        try:
            cs = collection_stats(f"{coll}_chunks")
            grand -= cs["count"]
            print(f"  {coll}_chunks: {cs['count']}")
        except Exception:
            print(f"  {coll}_chunks: (空)")
    print(f"  差异 (paper - sum): {grand} (应为0)")
    print(f"  总计复制: {total_copied} chunks")


if __name__ == "__main__":
    main()
