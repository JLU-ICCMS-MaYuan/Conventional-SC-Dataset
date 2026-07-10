"""
从 dev.db 读取 paper summary → embed → 写入 Chroma paper_summaries 集合。
用于 resolve_one_paper 快速匹配。
"""
import json
import os
import sqlite3
import sys
import time

DB_PATH = "/home/work/workshop/git/SC-Wiki-modules/dev.db"
COLLECTION_NAME = "paper_summaries"

# 确保用 SC-Wiki-modules 的 rag 模块
sys.path.insert(0, "/home/work/workshop/git/SC-Wiki-modules")
from backend.rag.ingest.embedder import embed_texts
from backend.rag.vectordb import _get_collection, _get_client


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, title, summary, keywords_tags, paper_type FROM papers"
    ).fetchall()
    conn.close()
    print(f"读取 {len(rows)} 篇论文")

    # 清理旧集合
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"删除旧集合 {COLLECTION_NAME}")
    except Exception:
        pass

    col = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"创建集合 {COLLECTION_NAME}")

    # 批量 embed (每批 50)
    batch_size = 50
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        # 搜索文本 = summary + keywords
        texts = []
        ids = []
        metadatas = []
        for pid, title, summary, keywords, paper_type in batch:
            search_text = summary or ""
            if keywords:
                try:
                    kw_list = json.loads(keywords)
                    search_text += " " + " ".join(kw_list)
                except (json.JSONDecodeError, TypeError):
                    pass
            texts.append(search_text)
            ids.append(str(pid))
            metadatas.append({
                "paper_id": str(pid),
                "title": title or "",
                "paper_type": paper_type or "",
            })

        embeddings = embed_texts(texts)
        col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        total += len(batch)
        print(f"  {total}/{len(rows)}")
        time.sleep(0.1)

    print(f"完成! {col.count()} 条")


if __name__ == "__main__":
    main()
