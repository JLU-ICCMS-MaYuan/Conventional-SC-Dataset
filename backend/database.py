"""
Database configuration.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# v2 库：papers 富化列 + key_properties 通用物性表（由 rebuild_from_clean_results.py 重建）
DEFAULT_DATABASE_URL = "mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset_v2?charset=utf8mb4"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
