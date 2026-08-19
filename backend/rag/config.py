"""SC-Wiki internal RAG configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_RAG_DATA_ROOT = (Path(__file__).resolve().parents[2]).resolve()


class RagSettings(BaseSettings):
    rag_data_root: Path = DEFAULT_RAG_DATA_ROOT
    rag_database_url: str | None = None
    rag_chroma_path: Path | None = None
    sc_wiki_data_dir: Path = Path("/data")
    redis_url: str = "redis://127.0.0.1:6379/0"
    upload_task_ttl_seconds: int = 24 * 60 * 60

    # Qdrant 配置
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_base_url: str = ""

    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def embedding_key(self) -> str:
        """Embedding API key，默认回退到 openai_api_key。"""
        return self.embedding_api_key or self.openai_api_key

    @property
    def embedding_url(self) -> str:
        """Embedding API base URL，默认回退到 openai_base_url。"""
        return self.embedding_base_url or self.openai_base_url

    # Brainstorm 配置
    brainstorm_max_clarify_rounds: int = 5
    brainstorm_max_agent_rounds: int = 3

    @property
    def data_root(self) -> Path:
        if self.rag_data_root is not None:
            return self.rag_data_root.expanduser().resolve()
        env_root = os.environ.get("RAG_DATA_ROOT")
        if env_root:
            return Path(env_root).expanduser().resolve()
        return (Path(__file__).resolve().parents[3] / "Conventional-SC-Dataset-talk").resolve()

    @property
    def database_url(self) -> str:
        if self.rag_database_url:
            return self.rag_database_url
        env_url = os.environ.get("RAG_DATABASE_URL")
        if env_url:
            return env_url
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url
        db_path = self.data_root / "dev.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def chroma_path(self) -> Path:
        """已废弃 - ChromaDB 已迁移至 Qdrant。保留以兼容旧配置。"""
        if self.rag_chroma_path is not None:
            return self.rag_chroma_path.expanduser().resolve()
        return self.data_root / "data" / "chroma_db"

    @property
    def database_available(self) -> bool:
        from urllib.parse import urlparse

        url = urlparse(self.database_url)
        if url.scheme and url.scheme.startswith("mysql"):
            try:
                import pymysql

                conn = pymysql.connect(
                    host=url.hostname or "127.0.0.1",
                    port=url.port or 3306,
                    user=url.username or "",
                    password=url.password or "",
                    database=(url.path or "/").lstrip("/") or "",
                    connect_timeout=3,
                )
                conn.close()
                return True
            except Exception:
                return False
        # SQLite fallback
        db_path = self.data_root / "dev.db"
        return db_path.exists()

    @property
    def chat_configured(self) -> bool:
        return bool(self.llm_api_key or self.deepseek_api_key)

    @property
    def completion_api_key(self) -> str:
        return self.llm_api_key or self.deepseek_api_key

    @property
    def completion_base_url(self) -> str:
        return self.llm_base_url or self.deepseek_base_url

    @property
    def completion_model(self) -> str:
        return self.llm_model or self.deepseek_model


@lru_cache(maxsize=1)
def get_rag_settings() -> RagSettings:
    return RagSettings()


settings = get_rag_settings()
