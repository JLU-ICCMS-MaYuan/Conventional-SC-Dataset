"""Safely run Alembic for both imported and newly created databases."""

from __future__ import annotations

import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


IMPORTED_SCHEMA_BASELINE = "b95420be551f"
ISSUE90_SAFE_HEAD = "issue90_copy_v1"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 环境变量未设置")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        tables = set(inspect(engine).get_table_names())
        has_version = False
        if "alembic_version" in tables:
            with engine.connect() as connection:
                has_version = connection.exec_driver_sql(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                ).first() is not None
    finally:
        engine.dispose()

    config = Config("alembic.ini")
    if "papers" in tables and not has_version:
        print(f"检测到已导入数据库，标记迁移基线 {IMPORTED_SCHEMA_BASELINE}")
        command.stamp(config, IMPORTED_SCHEMA_BASELINE)
    target = "head" if os.environ.get("ISSUE90_CONTRACT_CONFIRMED") == "1" else ISSUE90_SAFE_HEAD
    command.upgrade(config, target)


if __name__ == "__main__":
    main()
