"""
并行性能测试 — 测试各组件在多并发下的表现

用法: python backend/tests/test_concurrency.py [--workers 4]
"""

import sys
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure backend is importable in subprocesses
_proj_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _proj_root)
os.environ["PYTHONPATH"] = _proj_root + os.pathsep + os.environ.get("PYTHONPATH", "")

# ═══════════════════════════════════════════════
# 1. MySQL 并发查询
# ═══════════════════════════════════════════════

def _mysql_query(n: int) -> float:
    """单次 MySQL 查询"""
    from backend.database import SessionLocal
    from backend import models
    from sqlalchemy import func

    t0 = time.time()
    db = SessionLocal()
    try:
        db.query(func.count(models.Paper.id)).scalar()
    finally:
        db.close()
    return time.time() - t0


def test_mysql(workers: int = 4, rounds: int = 10):
    print(f"\n{'='*60}")
    print(f"📊 MySQL 并发查询 (workers={workers}, rounds={rounds})")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_mysql_query, i) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]

    print(f"  总耗时: {sum(times):.2f}s  |  平均: {sum(times)/len(times):.3f}s  |  "
          f"最快: {min(times):.3f}s  |  最慢: {max(times):.3f}s")


# ═══════════════════════════════════════════════
# 2. SQLAlchemy 批量 INSERT (key_properties 风格)
# ═══════════════════════════════════════════════

def _mysql_insert(n: int) -> float:
    """单次 INSERT 测试（不实际写表）"""
    from backend.database import SessionLocal
    from backend import models
    from sqlalchemy import text

    t0 = time.time()
    db = SessionLocal()
    try:
        # 只测连接+ping，不写数据
        db.execute(text("SELECT 1")).fetchone()
    finally:
        db.close()
    return time.time() - t0


def test_mysql_insert(workers: int = 4, rounds: int = 20):
    print(f"\n{'='*60}")
    print(f"📊 MySQL 并发连接 (workers={workers}, rounds={rounds})")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_mysql_insert, i) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]

    print(f"  总耗时: {sum(times):.2f}s  |  平均: {sum(times)/len(times):.3f}s  |  "
          f"最快: {min(times):.3f}s  |  最慢: {max(times):.3f}s")


# ═══════════════════════════════════════════════
# 3. ChromaDB 并发搜索
# ═══════════════════════════════════════════════

def _chroma_read(n: int) -> float:
    """单次 ChromaDB 并发读取（不触发 embedding 下载）"""
    from backend.rag.vectordb import _get_client, COLLECTION_NAME

    t0 = time.time()
    try:
        col = _get_client().get_collection(COLLECTION_NAME)
        col.get(limit=5)  # 读少量数据，测线程安全
    except Exception as e:
        print(f"  Chroma 错误: {type(e).__name__}: {e}")
        return -1
    return time.time() - t0


def test_chroma(workers: int = 4, rounds: int = 8):
    print(f"\n{'='*60}")
    print(f"📊 ChromaDB 并发读取 (workers={workers}, rounds={rounds})")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_chroma_read, i) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]
        times = [t for t in times if t >= 0]

    if times:
        ok = len(times)
        print(f"  成功: {ok}/{rounds}  |  平均: {sum(times)/len(times):.4f}s  |  "
              f"最快: {min(times):.4f}s  |  最慢: {max(times):.4f}s")


# ═══════════════════════════════════════════════
# 4. DeepSeek API 并发调用
# ═══════════════════════════════════════════════

def _llm_call(prompt: str) -> float:
    """单次 DeepSeek API 调用"""
    from openai import OpenAI
    from backend.rag.config import settings

    t0 = time.time()
    try:
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=50, stream=False)
    except Exception as e:
        print(f"  DeepSeek 错误: {e}")
        return -1
    return time.time() - t0


def test_deepseek(workers: int = 2, rounds: int = 4):
    print(f"\n{'='*60}")
    print(f"📊 DeepSeek API 并发调用 (workers={workers}, rounds={rounds})")

    prompts = ["1+1=?", "Say hello in Chinese.", "What is 2^10?",
               "Name one element."]

    if workers > 2:
        print("  ⚠️  DeepSeek 免费 API 限并发 2，已限制")
        workers = 2

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_llm_call, prompts[i % len(prompts)]) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]
        times = [t for t in times if t >= 0]

    if times:
        print(f"  总耗时: {sum(times):.2f}s  |  平均: {sum(times)/len(times):.3f}s  |  "
              f"最快: {min(times):.3f}s  |  最慢: {max(times):.3f}s")


# ═══════════════════════════════════════════════
# 5. Embedding API 并发调用
# ═══════════════════════════════════════════════

def _embedding_call(text: str) -> float:
    from openai import OpenAI
    from backend.rag.config import settings

    t0 = time.time()
    try:
        client = OpenAI(api_key=settings.embedding_api_key, base_url=settings.embedding_base_url)
        resp = client.embeddings.create(input=[text], model="BAAI/bge-m3")
    except Exception as e:
        print(f"  Embedding 错误: {e}")
        return -1
    return time.time() - t0


def test_embedding(workers: int = 2, rounds: int = 4):
    print(f"\n{'='*60}")
    print(f"📊 Embedding API 并发调用 (workers={workers}, rounds={rounds})")

    texts = ["superconductor", "hydride", "high pressure", "DFT"]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_embedding_call, texts[i % len(texts)]) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]
        times = [t for t in times if t >= 0]

    if times:
        print(f"  总耗时: {sum(times):.2f}s  |  平均: {sum(times)/len(times):.3f}s  |  "
              f"最快: {min(times):.3f}s  |  最慢: {max(times):.3f}s")


# ═══════════════════════════════════════════════
# 6. Neo4j 并发查询
# ═══════════════════════════════════════════════

def _neo4j_query(query: str) -> float:
    from neo4j import GraphDatabase
    import os

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "scwiki123")

    t0 = time.time()
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as s:
            s.run(query)
        driver.close()
    except Exception as e:
        print(f"  Neo4j 错误: {type(e).__name__}")
        return -1
    return time.time() - t0


def test_neo4j(workers: int = 4, rounds: int = 8):
    print(f"\n{'='*60}")
    print(f"📊 Neo4j 并发查询 (workers={workers}, rounds={rounds})")

    query = "MATCH (n) RETURN count(n) LIMIT 1"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_neo4j_query, query) for i in range(rounds)]
        times = [f.result() for f in as_completed(futures)]
        times = [t for t in times if t >= 0]

    if times:
        print(f"  总耗时: {sum(times):.2f}s  |  平均: {sum(times)/len(times):.3f}s  |  "
              f"最快: {min(times):.3f}s  |  最慢: {max(times):.3f}s")


# ═══════════════════════════════════════════════
# 7. Async I/O vs Thread 对比
# ═══════════════════════════════════════════════

async def _async_mysql() -> float:
    from backend.rag.database import async_session_factory
    from sqlalchemy import text

    t0 = time.time()
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    return time.time() - t0


def test_async_vs_thread(rounds: int = 20):
    print(f"\n{'='*60}")
    print(f"📊 Async I/O vs ThreadPool (MySQL, rounds={rounds})")

    # Async
    async def _run_async():
        return await asyncio.gather(*[_async_mysql() for _ in range(rounds)])

    t0 = time.time()
    async_times = asyncio.run(_run_async())
    async_total = time.time() - t0

    # Thread pool
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_mysql_insert, i) for i in range(rounds)]
        thread_times = [f.result() for f in as_completed(futures)]
    thread_total = time.time() - t0

    print(f"  Async   — 总耗时: {async_total:.2f}s  平均: {sum(async_times)/len(async_times):.3f}s")
    print(f"  Thread  — 总耗时: {thread_total:.2f}s  平均: {sum(thread_times)/len(thread_times):.3f}s")
    print(f"  Async 快 {thread_total/async_total:.1f}x" if async_total < thread_total
          else f"  Thread 快 {async_total/thread_total:.1f}x")


# ═══════════════════════════════════════════════

def main():
    workers = 4
    for i, a in enumerate(sys.argv):
        if a == "--workers" and i + 1 < len(sys.argv):
            workers = int(sys.argv[i + 1])

    print("🧪 并行性能测试")
    print(f"   workers={workers}")
    print(f"   DeepSeek API: 免费版限 2 并发")

    # 基础组件
    test_mysql(workers=workers)
    test_mysql_insert(workers=workers)

    # 向量 & 图谱
    test_chroma(workers=workers)

    # 外部 API (限并发)
    test_deepseek(workers=min(workers, 2))

    # 对比测试
    test_async_vs_thread()

    # 可选（需要 Neo4j 运行）
    if "--all" in sys.argv:
        test_embedding(workers=min(workers, 2))
        test_neo4j(workers=workers)

    print(f"\n{'='*60}")
    print("✅ 测试完成")

if __name__ == "__main__":
    main()
