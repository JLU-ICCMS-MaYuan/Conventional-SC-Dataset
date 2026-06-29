"""SC-Wiki internal RAG configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_RAG_DATA_ROOT = (Path(__file__).resolve().parents[3] / "Conventional-SC-Dataset-talk").resolve()


class RagSettings(BaseSettings):
    rag_data_root: Path = DEFAULT_RAG_DATA_ROOT
    rag_database_url: str | None = None
    rag_chroma_path: Path | None = None

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
        db_path = self.data_root / "dev.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def chroma_path(self) -> Path:
        if self.rag_chroma_path is not None:
            return self.rag_chroma_path.expanduser().resolve()
        env_path = os.environ.get("RAG_CHROMA_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()
        return self.data_root / "chroma_db"

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
        return bool(self.deepseek_api_key)


@lru_cache(maxsize=1)
def get_rag_settings() -> RagSettings:
    return RagSettings()


settings = get_rag_settings()
