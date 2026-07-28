"""
论文摘要向量索引: MySQL papers → embed → Qdrant paper_summaries
用于 fix_resolve.py V2 快速论文匹配。

用法: python backend/scripts/build_summary_index.py
"""

import json
import time

from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.ingest.embedder import embed_texts
from backend.database import DATABASE_URL as MYSQL_URL

COLLECTION_NAME = "paper_summaries"
QDRANT_HOST = "127.0.0.1"
QDRANT_PORT = 6333
BATCH_SIZE = 50


def main():
    engine = create_engine(MYSQL_URL)
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT id, title, summary, keywords_tags, paper_type
            FROM papers
            WHERE summary IS NOT NULL AND summary != ''
        """)).fetchall()
    print(f"MySQL 读取 {len(rows)} 篇论文")

    # Qdrant 客户端
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 删除旧集合并重建
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"删除旧集合 {COLLECTION_NAME}")
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]

        texts = []
        ids = []
        metadatas = []
        for pid, title, summary, keywords, paper_type in batch:
            search_text = (summary or "")
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

        points = [
            PointStruct(
                id=int(pid) if pid.isdigit() else abs(hash(pid)) % (10 ** 15),
                vector=emb,
                payload={
                    "document": texts[j],
                    **metadatas[j],
                },
            )
            for j, (pid, emb) in enumerate(zip(ids, embeddings))
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total += len(batch)
        print(f"  {total}/{len(rows)}")
        time.sleep(0.1)

    info = client.get_collection(COLLECTION_NAME)
    print(f"完成! {info.points_count} 条")


if __name__ == "__main__":
    main()
