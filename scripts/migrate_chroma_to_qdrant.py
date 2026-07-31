#!/usr/bin/env python3
"""从 ChromaDB 迁移向量数据到 Qdrant"""

import chromadb, uuid, time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

CHROMA_PATH = "/home/guoqiang/SC-Wiki/data/chroma_db_backup"
QDRANT_HOST = "127.0.0.1"
QDRANT_PORT = 6333
BATCH_SIZE = 500

def main():
    # 连接源（ChromaDB）和目标（Qdrant）
    print("连接 ChromaDB...")
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)

    print("连接 Qdrant...")
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    collections = chroma.list_collections()
    print(f"找到 {len(collections)} 个集合\n")

    for col in collections:
        name = col.name
        count = col.count()
        print(f"迁移 {name}: {count} 条向量...")

        if count == 0:
            print(f"  跳过（空集合）")
            continue

        # 获取全部数据
        result = col.get(include=['embeddings', 'documents', 'metadatas'])
        vectors = result['embeddings']
        documents = result['documents'] or [''] * len(vectors)
        metadatas = result['metadatas'] or [{}] * len(vectors)
        ids = result['ids']

        dim = len(vectors[0])

        # 删除 Qdrant 上已存在的同名集合，重建
        try:
            qdrant.delete_collection(name)
        except:
            pass

        qdrant.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

        # 分批写入 Qdrant
        total = len(vectors)
        for i in range(0, total, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, total)
            points = []
            for j in range(i, batch_end):
                # 将 metadata 中的 None 值转为字符串
                meta = {k: (str(v) if v is None else v) for k, v in metadatas[j].items()} if metadatas[j] else {}

                points.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}_{ids[j]}")),
                    "vector": vectors[j],
                    "payload": {
                        "document": documents[j] if j < len(documents) else "",
                        **meta
                    }
                })

            qdrant.upsert(collection_name=name, points=points)
            print(f"  {batch_end}/{total} ({batch_end*100//total}%)")

        print(f"  ✓ 完成\n")

    print("全部迁移完成！")
    print(f"共 {len(collections)} 个集合，总向量数: {sum(c.count() for c in collections)}")

if __name__ == "__main__":
    start = time.time()
    main()
    print(f"耗时: {time.time() - start:.1f} 秒")
