"""
数据库引擎与会话管理模块。

使用 SQLAlchemy 2.0 异步 API:
- create_async_engine → AsyncEngine
- async_sessionmaker  → AsyncSession

这种模式是生产级 FastAPI + SQLAlchemy 应用的标准做法。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.rag.config import settings

# ── 引擎 ────────────────────────────────────────────────────────────────
# 连接池: pool_size=5 是默认值，可根据并发负载调整
# echo=True 会在开发时打印所有 SQL 语句
# SQLite 不支持 pool_size/max_overflow，只在 MySQL 下使用
import re
_engine_kw = {"echo": settings.debug}
if not re.search(r"sqlite", settings.database_url, re.I):
    _engine_kw["pool_size"] = 5
    _engine_kw["max_overflow"] = 10

engine = create_async_engine(settings.database_url, **_engine_kw)

# ── Session 工厂 ───────────────────────────────────────────────────────
# async_sessionmaker 每次调用返回一个独立的 AsyncSession 实例
# 每个请求应创建自己的 session，请求结束后关闭
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── ORM 基类 ────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """所有模型继承此基类。SQLAlchemy 2.0 推荐用 DeclarativeBase 而非 declarative_base()。"""


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI 依赖注入用。每个请求创建一个 session，请求结束时关闭。"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """开发环境下自动建表。生产环境应通过 Alembic 迁移管理。

    这里从 hydride_rag.database 导入 Base（本模块定义的基类），
    同时需要导入所有模型子类以确保它们被 Base.metadata 注册。
    """
    # 导入所有模型，确保 metadata 完整
    import backend.rag.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
