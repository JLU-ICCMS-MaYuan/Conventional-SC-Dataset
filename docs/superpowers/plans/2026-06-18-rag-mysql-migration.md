# RAG MySQL 迁移实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 RAG 系统的数据库层从 SQLite 切换到 MySQL，复用主应用已有的 `superconductor_dataset` 数据库。

**Architecture:** 通过环境变量 `RAG_DATABASE_URL` 注入 MySQL 连接字符串，config.py 读取后传递给 SQLAlchemy async engine。knowledge_graph.py 从 raw sqlite3 重写为 SQLAlchemy async。health check 从文件存在检查改为数据库连接测试。

**Tech Stack:** SQLAlchemy 2.0 async + asyncmy + pymysql

---

### Task 1: 修改 config.py 支持 MySQL database_url

**Files:**
- Modify: `backend/rag/config.py:41-46`

- [ ] **Step 1: 更改 database_url 属性**

将 `database_url` 从硬编码 SQLite 改为优先读取 `RAG_DATABASE_URL` 环境变量：

```python
@property
def database_url(self) -> str:
    if self.rag_database_url:
        return self.rag_database_url
    env_url = os.environ.get("RAG_DATABASE_URL")
    if env_url:
        return env_url
    db_path = self.data_root / "dev.db"
    return f"sqlite+aiosqlite:///{db_path}"
```

- [ ] **Step 2: 添加 database_available 属性**

在 `RagSettings` 类中添加同步连接检测（供 health 用）：

```python
@property
def database_available(self) -> bool:
    try:
        import pymysql
        from urllib.parse import urlparse
        url = urlparse(self.database_url)
        if url.scheme.startswith("mysql"):
            conn = pymysql.connect(
                host=url.hostname or "127.0.0.1",
                port=url.port or 3306,
                user=url.username or "",
                password=url.password or "",
                database=url.path.lstrip("/") or "",
                connect_timeout=3,
            )
            conn.close()
            return True
        elif "sqlite" in url.scheme:
            db_path = self.data_root / "dev.db"
            return db_path.exists()
    except Exception:
        return False
    return False
```

- [ ] **Step 3: 验证 config 解析**

```bash
RAG_DATABASE_URL="mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4" PYTHONPATH="." python -c "from backend.rag.config import get_rag_settings; s=get_rag_settings(); print(s.database_url); print(s.database_available)"
```

Expected: 输出 MySQL URL 和 `True`

- [ ] **Step 4: 验证 SQLite fallback**

```bash
RAG_DATABASE_URL="" PYTHONPATH="." python -c "from backend.rag.config import get_rag_settings; s=get_rag_settings(); print(s.database_url)"
```

Expected: 输出 `sqlite+aiosqlite:///.../dev.db`

- [ ] **Step 5: Commit**

```bash
git add backend/rag/config.py
git commit -m "feat: add MySQL database_url support to RAG config"
```

---

### Task 2: 重写 knowledge_graph.py 为 SQLAlchemy async

**Files:**
- Modify: `backend/rag/knowledge_graph.py` (全文重写)

- [ ] **Step 1: 重写 knowledge_graph.py**

删除所有 `sqlite3` 引用，改为 SQLAlchemy async + `async_session_factory`：

```python
"""
knowledge_graph.py — 知识图谱查询模块。

使用 SQLAlchemy async 查询 superconductor_records / superconductors / papers。
支持 MySQL 和 SQLite，由 RAG_DATABASE_URL 配置决定。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.sql import func

from backend.rag.database import async_session_factory
from backend.rag.models import Paper, Superconductor, SuperconductorRecord

FIELD_MAP = {
    "超导温度(AD)": SuperconductorRecord.allen_dynes_tc,
    "压力": SuperconductorRecord.pressure_gpa,
    "电声耦合lambda": SuperconductorRecord.lambda_value,
}


async def query(
    predicate: str,
    operator: str = "=",
    value: str | None = None,
) -> list[dict]:
    """查询知识图谱。

    predicate 映射到数据库字段：
      "超导温度(AD)" → superconductor_records.allen_dynes_tc
      "压力"         → superconductor_records.pressure_gpa
      "电声耦合lambda"   → superconductor_records.lambda_value

    Returns:
        [{"subject": "LaH10", "predicate": "超导温度(AD)", "object": "250"}, ...]
    """
    field = FIELD_MAP.get(predicate)
    if field is None:
        return []

    async with async_session_factory() as session:
        stmt = (
            select(
                Superconductor.chemical_formula,
                field,
                Paper.id,
                Paper.title,
            )
            .select_from(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(field.isnot(None))
            .where(Paper.review_status == "approved")
        )

        if operator in (">", "<", ">=", "<=") and value is not None:
            try:
                val = float(value)
            except ValueError:
                return []
            if operator == ">":
                stmt = stmt.where(field > val)
            elif operator == "<":
                stmt = stmt.where(field < val)
            elif operator == ">=":
                stmt = stmt.where(field >= val)
            elif operator == "<=":
                stmt = stmt.where(field <= val)
        elif operator == "=" and value:
            try:
                val = float(value)
            except ValueError:
                return []
            stmt = stmt.where(field == val)

        stmt = stmt.order_by(field.desc()).distinct()

        result = await session.execute(stmt)
        rows = result.all()

    return [
        {
            "subject": row.chemical_formula,
            "predicate": predicate,
            "object": str(row[1]),
            "paper_id": row[2],
            "paper_title": row[3],
        }
        for row in rows
    ]


async def get_all_properties(subject: str) -> list[dict]:
    """获取某超导体的所有属性。"""
    async with async_session_factory() as session:
        stmt = (
            select(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Superconductor.chemical_formula == subject)
            .where(Paper.review_status == "approved")
            .limit(1)
        )
        result = await session.execute(stmt)
        rec = result.scalars().first()

    if rec is None:
        return []

    props = []
    labels = [
        ("超导温度(AD)", "allen_dynes_tc"),
        ("实验Tc", "experimental_tc"),
        ("压力", "pressure_gpa"),
        ("电声耦合lambda", "lambda_value"),
        ("声子频率ω_log", "omega_log"),
        ("空间群", "space_group_symbol"),
    ]
    for label, key in labels:
        val = getattr(rec, key, None)
        if val is not None:
            props.append({"predicate": label, "object": str(val)})
    return props


async def delete_paper_triples(paper_id: int) -> int:
    """删除某篇论文的数据。"""
    from sqlalchemy import delete

    async with async_session_factory() as session:
        stmt = delete(SuperconductorRecord).where(SuperconductorRecord.paper_id == paper_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def stats() -> dict:
    """返回知识图谱统计信息。"""
    async with async_session_factory() as session:
        subj_stmt = (
            select(func.count(func.distinct(Superconductor.chemical_formula)))
            .select_from(SuperconductorRecord)
            .join(Superconductor, Superconductor.id == SuperconductorRecord.superconductor_id)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Paper.review_status == "approved")
        )
        subjects = (await session.execute(subj_stmt)).scalar() or 0

        rec_stmt = (
            select(func.count())
            .select_from(SuperconductorRecord)
            .join(Paper, Paper.id == SuperconductorRecord.paper_id)
            .where(Paper.review_status == "approved")
        )
        records = (await session.execute(rec_stmt)).scalar() or 0

    return {"subjects": subjects, "triples": records}
```

- [ ] **Step 2: 验证 knowledge_graph query 同步调用点不再存在**

```bash
rg -n "from backend.rag.knowledge_graph import|kg_query\(|get_all_properties\(" backend/rag/rag/engine.py
```

Expected: 确认 engine.py 中有调用，后续 Task 3 会改为 await。

- [ ] **Step 3: Commit**

```bash
git add backend/rag/knowledge_graph.py
git commit -m "refactor: rewrite knowledge_graph from raw sqlite3 to SQLAlchemy async"
```

---

### Task 3: 修改 engine.py 中 knowledge_graph 调用为 await

**Files:**
- Modify: `backend/rag/rag/engine.py:168-202` (ask 函数中 KG 部分)
- Modify: `backend/rag/rag/engine.py:320-370` (ask_stream 函数中 KG 部分)

- [ ] **Step 1: 在 ask() 中将 kg_query 和 get_all_properties 改为 await**

在 `ask()` 函数第 181-192 行，将同步调用改为 await：

```python
# 原来: kg_results = kg_query(predicate, operator=op, value=val)
# 改为:
kg_results = await kg_query(predicate, operator=op, value=val)

# 原来: props = get_all_properties(subj)
# 改为:
props = await get_all_properties(subj)
```

- [ ] **Step 2: 在 ask_stream() 中同样改为 await**

在 `ask_stream()` 函数第 330-350 行，同样将同步调用改为 await：

```python
kg_results = await kg_query(predicate, operator=op, value=val)
# ...
props = await get_all_properties(subj)
```

- [ ] **Step 3: 验证无遗漏同步调用**

```bash
rg -n "kg_query\(|get_all_properties\(" backend/rag/rag/engine.py
```

Expected: 所有调用前都有 `await`。

- [ ] **Step 4: Commit**

```bash
git add backend/rag/rag/engine.py
git commit -m "fix: await async knowledge_graph calls in engine"
```

---

### Task 4: 修改 service.py 健康检查

**Files:**
- Modify: `backend/rag/service.py:31-68`

- [ ] **Step 1: 重写 health() 函数**

删除 `_sqlite_path_from_url()`，用 `settings.database_available` 替代文件存在检查：

```python
def health() -> dict[str, Any]:
    settings = get_rag_settings()
    database_available = settings.database_available
    chroma_available = settings.chroma_path.exists()
    chat_available = settings.chat_configured
    available = database_available and chroma_available

    if not available:
        message = "AI 文献助手数据不可用"
    elif not chat_available:
        message = "RAG 检索可用，LLM 问答未配置"
    else:
        message = "AI 文献助手已就绪"

    return {
        "available": available,
        "database_available": database_available,
        "chroma_available": chroma_available,
        "chat_available": chat_available,
        "message": message,
    }
```

同时删除 `_sqlite_path_from_url()` 函数（第 31-35 行）。

- [ ] **Step 2: Commit**

```bash
git add backend/rag/service.py
git commit -m "refactor: use MySQL connection test for RAG health check"
```

---

### Task 5: 在 MySQL 创建 paper_chunks 表并迁移数据

**Files:**
- Create: `scripts/migrate_paper_chunks_to_mysql.py` (一次性脚本)

- [ ] **Step 1: 写迁移脚本**

```python
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
    from backend.rag.database import engine, Base
    import backend.rag.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
```

- [ ] **Step 2: 执行迁移**

```bash
RAG_DATABASE_URL="mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4" PYTHONPATH="." conda run -n Conventional-SC-Dataset python scripts/migrate_paper_chunks_to_mysql.py
```

Expected: `迁移完成`，MySQL paper_chunks 总计 29369。

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_paper_chunks_to_mysql.py
git commit -m "feat: add paper_chunks mysql migration script"
```

---

### Task 6: 更新测试

**Files:**
- Modify: `tests/test_rag_service.py`

- [ ] **Step 1: 更新 test_health_reports_missing_data - 改为 MySQL 连接失败场景**

```python
def test_health_reports_missing_data_when_mysql_unreachable(monkeypatch):
    monkeypatch.setenv("RAG_DATABASE_URL", "mysql+asyncmy://nobody:bad@127.0.0.1:3306/nonexistent_db")
    monkeypatch.setenv("RAG_CHROMA_PATH", "/nonexistent/chroma")
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is False
    assert status["database_available"] is False
    assert status["chroma_available"] is False
    assert status["chat_available"] is False
    assert status["message"] == "AI 文献助手数据不可用"
```

- [ ] **Step 2: 更新 test_health_reports_search_available_without_llm**

```python
def test_health_reports_search_available_without_llm(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_dir))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True
    assert status["chat_available"] is False
    assert status["message"] == "RAG 检索可用，LLM 问答未配置"
```

- [ ] **Step 3: 添加 knowledge_graph async query 测试**

```python
@pytest.mark.asyncio
async def test_knowledge_graph_query_async(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    db_path = data_root / "dev.db"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT, review_status TEXT);
        CREATE TABLE superconductors (id INTEGER PRIMARY KEY, chemical_formula TEXT);
        CREATE TABLE superconductor_records (
            id INTEGER PRIMARY KEY,
            superconductor_id INTEGER,
            paper_id INTEGER,
            allen_dynes_tc REAL
        );
        INSERT INTO papers VALUES (1, 'Test', 'approved');
        INSERT INTO superconductors VALUES (1, 'TestH10');
        INSERT INTO superconductor_records VALUES (1, 1, 1, 321.0);
    """)
    conn.commit()
    conn.close()

    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    get_rag_settings.cache_clear()

    from backend.rag import knowledge_graph as kg

    rows = await kg.query("超导温度(AD)", operator=">", value="300")

    assert rows == [{
        "subject": "TestH10",
        "predicate": "超导温度(AD)",
        "object": "321.0",
        "paper_id": 1,
        "paper_title": "Test",
    }]
```

- [ ] **Step 4: 更新 test_knowledge_graph_uses_configured_rag_data_root**

删除旧测试，用上面新的 async 测试替代。

- [ ] **Step 5: 运行测试套件验证**

```bash
RAG_DATABASE_URL="mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4" PYTHONPATH="." conda run -n Conventional-SC-Dataset pytest tests/test_rag_internal_imports.py tests/test_rag_service.py tests/test_rag_internal_api.py tests/test_rag_page.py -q
```

Expected: 全部通过。

- [ ] **Step 6: Commit**

```bash
git add tests/test_rag_service.py
git commit -m "test: update RAG tests for MySQL migration"
```

---

### Task 7: 更新启动配置和 .env

**Files:**
- Modify: `.env` (追加 RAG_DATABASE_URL)

- [ ] **Step 1: 在 .env 追加 RAG_DATABASE_URL**

```
RAG_DATABASE_URL=mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4
```

- [ ] **Step 2: 重启服务并验证**

```bash
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
RAG_DATA_ROOT="/home/work/workshop/git/Conventional-SC-Dataset-talk" PYTHONPATH="." conda run -n Conventional-SC-Dataset uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

验证：

```bash
curl -sS http://127.0.0.1:8000/api/rag/health
# Expected: {..., "database_available": true, "chat_available": true, "message": "AI 文献助手已就绪"}

curl -sS http://127.0.0.1:8000/api/rag/stats
# Expected: papers=638, paper_chunks 出现在统计中
```

- [ ] **Step 3: Commit**

```bash
git add .env
git commit -m "chore: add RAG_DATABASE_URL to .env"
```

---

### 验证清单

- [ ] `GET /api/rag/health` → `database_available: true`
- [ ] `GET /api/rag/stats` → 包含 paper_chunks 统计
- [ ] `POST /api/rag/chat` "LaH10 的 Tc 是多少" → 有回答
- [ ] `POST /api/rag/chat` "超导温度高于 200K 的有哪些" → 有结构化 KG 结果
- [ ] `POST /api/rag/chat/stream` 同上 → SSE 流式正常
- [ ] `GET /api/rag/search?q=LaH10` → 有结果
- [ ] `GET /api/rag/papers?keyword=hydride` → 有论文列表
- [ ] `POST /api/rag/upload-pdf` → 摄入到 MySQL
- [ ] 测试套件全部通过
