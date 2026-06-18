"""一次性脚本：将 paper_chunks 从 SQLite 迁移到 MySQL。"""

import asyncio
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main():
    os.environ.setdefault(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )

    # 1. 在 MySQL 建表
    from backend.rag.database import engine
    import backend.rag.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(backend.rag.database.Base.metadata.create_all)

    print("MySQL 表创建完成")

    # 2. 从 SQLite 读数据
    sqlite_path = "/home/work/workshop/git/Conventional-SC-Dataset-talk/dev.db"
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    rows = sqlite_conn.execute(
        "SELECT id, paper_id, chunk_index, section_name, heading, content, token_count FROM paper_chunks"
    ).fetchall()
    sqlite_conn.close()
    print(f"SQLite 读取 {len(rows)} 条 paper_chunks")

    # 3. 写入 MySQL
    from backend.rag.database import async_session_factory
    from backend.rag.models import PaperChunk
    from sqlalchemy import select, func

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        async with async_session_factory() as session:
            for row in batch:
                existing = await session.execute(
                    select(func.count()).select_from(PaperChunk).where(PaperChunk.id == row["id"])
                )
                if existing.scalar() > 0:
                    continue
                chunk = PaperChunk(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    chunk_index=row["chunk_index"],
                    section_name=row["section_name"],
                    heading=row["heading"],
                    content=row["content"],
                    token_count=row["token_count"],
                )
                session.add(chunk)
            await session.commit()
        print(f"  已迁移 {min(i + batch_size, len(rows))}/{len(rows)}")

    # 4. 验证
    async with async_session_factory() as session:
        count = (await session.execute(select(func.count()).select_from(PaperChunk))).scalar()
    print(f"MySQL paper_chunks 总计: {count}")
    assert count == len(rows), f"数量不匹配: {count} != {len(rows)}"
    print("迁移完成")


if __name__ == "__main__":
    asyncio.run(main())
