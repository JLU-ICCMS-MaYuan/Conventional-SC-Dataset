"""只写新建的本地 SQLite；用于官方来源解析的有限在线验证。"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.news.domain import SOURCES
from backend.news.models import NewsFeedItem, NewsFeedIdentity, NewsFeedSource
from backend.news.service import collect_source
from backend.news.sources import Sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, help="尚不存在的测试 SQLite 绝对路径")
    args = parser.parse_args()
    target = Path(args.database)
    if not target.is_absolute() or target.exists() or not target.parent.is_dir():
        parser.error("只允许已有目录下、尚不存在的 SQLite 绝对路径")
    engine = create_engine("sqlite:///" + str(target))
    for table in (NewsFeedItem.__table__, NewsFeedIdentity.__table__, NewsFeedSource.__table__):
        table.create(engine)
    source = Sources(max_pages=5)
    try:
        for name in SOURCES:
            ok = collect_source(engine, name, source, datetime.now(timezone.utc), initial_days=7)
            with Session(engine) as db:
                state = db.get(NewsFeedSource, name)
                print(f"{name}: success={ok} fetched={state.fetched} accepted={state.accepted} error={state.error_code}", flush=True)
    finally:
        source.transport.close()
        engine.dispose()


if __name__ == "__main__":
    main()

