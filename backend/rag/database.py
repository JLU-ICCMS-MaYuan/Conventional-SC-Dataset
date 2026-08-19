"""
数据库引擎与会话管理模块。

使用 SQLAlchemy 2.0 异步 API:
- create_async_engine → AsyncEngine
- async_sessionmaker  → AsyncSession

这种模式是生产级 FastAPI + SQLAlchemy 应用的标准做法。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.rag.config import settings

# ── 引擎 ────────────────────────────────────────────────────────────────
import re
_engine_kw = {"echo": settings.debug}
if not re.search(r"sqlite", settings.database_url, re.I):
    _engine_kw["pool_size"] = 5
    _engine_kw["max_overflow"] = 10
    _engine_kw["pool_pre_ping"] = True
    _engine_kw["pool_recycle"] = 3600

database_url = settings.database_url
if database_url.startswith("mysql+pymysql://"):
    database_url = database_url.replace("mysql+pymysql://", "mysql+asyncmy://", 1)
elif database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+asyncmy://", 1)
elif database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

engine = create_async_engine(database_url, **_engine_kw)

# ── Session 工厂 ───────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI 依赖注入用。每个请求创建一个 session，请求结束时关闭。"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """开发环境下自动建表。生产环境应通过 Alembic 迁移管理。"""
    import backend.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
