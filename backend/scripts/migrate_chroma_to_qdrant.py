"""
ChromaDB → Qdrant 数据迁移脚本

直接从 ChromaDB 搬运向量到 Qdrant。
重要：必须先读取所有 ChromaDB 数据，再导入 qdrant_client（避免 numpy 冲突）。

用法:
    python backend/scripts/migrate_chroma_to_qdrant.py [--batch-size 2000] [--collection paper_chunks]
"""

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

_proj_root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.insert(0, _proj_root)

# ⚠️ 先导入 chromadb（必须在 qdrant_client 之前）
import chromadb
from chromadb.config import Settings

QDRANT_HOST = os.environ.get("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
CHROMA_PATH = os.environ.get("RAG_CHROMA_PATH", "data/chroma_db")


def get_chroma_client():
    os.environ["CHROMADB_TELEMETRY"] = "false"
    return chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )


def read_all_from_chroma(collection_name: str, batch_size: int = 2000):
    """从 ChromaDB 读取全部数据（必须在导入 qdrant_client 之前调用）。"""
    client = get_chroma_client()
    col = client.get_collection(collection_name)
    total = col.count()

    if total == 0:
        return [], 0

    print(f"    读取 ChromaDB 数据...")
    all_ids = []
    all_docs = []
    all_meta = []
    all_emb = []

    offset = 0
    while offset < total:
        chunk = min(batch_size, total - offset)
        result = col.get(
            limit=chunk, offset=offset,
            include=["embeddings", "documents", "metadatas"],
        )
        all_ids.extend(result["ids"])
        all_docs.extend(result["documents"] if result["documents"] is not None else [])
        all_meta.extend(result["metadatas"] if result["metadatas"] is not None else [])
        # embeddings 是 numpy 数组列表，立即转为 Python list
        emb_list = result["embeddings"] if result["embeddings"] is not None else []
        all_emb.extend([e.tolist() if hasattr(e, 'tolist') else list(e) for e in emb_list])

        offset += chunk
        if offset % 5000 == 0:
            print(f"      已读 {offset}/{total}")

    dim = len(all_emb[0]) if all_emb else 1536
    print(f"    读取完成: {total} 条, 维度 {dim}")
    return (all_ids, all_docs, all_meta, all_emb), dim


def write_to_qdrant(collection_name: str, ids, docs, meta, emb, dim: int):
    """将数据写入 Qdrant（此时导入 qdrant_client）。"""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # 重建集合
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    # 批量写入（Qdrant HTTP 限制 32MB payload）
    BATCH = 500
    total = len(ids)
    migrated = 0
    start = time.time()

    for i in range(0, total, BATCH):
        end = min(i + BATCH, total)
        points = []
        for j in range(i, end):
            cid = ids[j]
            payload = {
                "document": docs[j] if docs[j] else "",
                **(meta[j] if meta[j] is not None else {}),
            }
            point_id = int(cid) if cid.isdigit() else abs(hash(cid)) % (10 ** 15)
            points.append(PointStruct(id=point_id, vector=emb[j], payload=payload))

        client.upsert(collection_name=collection_name, points=points)
        migrated = end
        elapsed = time.time() - start
        rate = migrated / elapsed if elapsed > 0 else 0
        pct = migrated / total * 100
        print(f"    {migrated}/{total} ({pct:.1f}%) — {rate:.0f} docs/s")

    elapsed = time.time() - start
    print(f"    写入完成: {total} 条, 耗时 {elapsed:.1f}s")
    return total


def migrate_collection(collection_name: str, batch_size: int = 2000, dry_run: bool = False):
    """迁移单个集合。"""
    print(f"  [{collection_name}] 开始...")

    # Phase 1: 从 ChromaDB 读取（在导入 qdrant_client 之前）
    (ids, docs, meta, emb), dim = read_all_from_chroma(collection_name, batch_size)

    if not ids:
        print(f"    空集合，跳过")
        return 0

    if dry_run:
        print(f"    [DRY-RUN] 将迁移 {len(ids)} 条记录")
        return 0

    # Phase 2: 写入 Qdrant
    return write_to_qdrant(collection_name, ids, docs, meta, emb, dim)


def main():
    parser = argparse.ArgumentParser(description="ChromaDB → Qdrant 迁移")
    parser.add_argument("--batch-size", type=int, default=2000, help="ChromaDB 读批次大小")
    parser.add_argument("--collection", type=str, default=None, help="仅迁移指定集合")
    parser.add_argument("--dry-run", action="store_true", help="仅统计")
    args = parser.parse_args()

    print("=" * 60)
    print("ChromaDB → Qdrant 数据迁移（两阶段：读 → 写）")
    print(f"  Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"  Chroma: {CHROMA_PATH}")
    print("=" * 60)

    # 获取集合列表
    chroma_client = get_chroma_client()
    if args.collection:
        collection_names = [args.collection]
    else:
        collection_names = [c.name for c in chroma_client.list_collections()]

    name_counts = []
    for name in collection_names:
        try:
            col = chroma_client.get_collection(name)
            name_counts.append((name, col.count()))
        except Exception as e:
            print(f"  跳过 {name}: {e}")
    name_counts.sort(key=lambda x: x[1])

    total_migrated = 0
    total_start = time.time()

    for name, count in name_counts:
        try:
            n = migrate_collection(name, batch_size=args.batch_size, dry_run=args.dry_run)
            total_migrated += n
        except Exception as e:
            print(f"  [{name}] 失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"总迁移: {total_migrated} 条, 耗时 {total_elapsed:.1f}s")

    # 验证
    from qdrant_client import QdrantClient
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print("\nQdrant 集合概览:")
    for col_info in qc.get_collections().collections:
        info = qc.get_collection(col_info.name)
        print(f"  {col_info.name:40s}  vectors: {info.points_count:>8d}")


if __name__ == "__main__":
    main()
