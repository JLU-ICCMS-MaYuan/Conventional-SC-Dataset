"""运行：python -m backend.news {collect,schedule,worker}。"""
import argparse
import logging
import os
import time

from backend.rq_runtime import run_worker_forever
from .domain import SOURCES
from .scheduler import QUEUE_NAME, redis_connection, run_job, schedule_forever


def run_worker(worker_cls, connection_factory=redis_connection, sleep=time.sleep):
    """RQ 空闲超时或 Redis 短暂故障后重建资讯 Worker。"""
    run_worker_forever(
        lambda: worker_cls([QUEUE_NAME], connection=connection_factory()),
        lambda worker: worker.work(),
        label="news worker",
        sleep=sleep,
    )


def main():
    parser = argparse.ArgumentParser(description="SC-Wiki 独立资讯采集")
    parser.add_argument("command", choices=("collect", "schedule", "worker"))
    parser.add_argument("--source", choices=(*SOURCES, "all"), default="all")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # 拒绝错误配置；不在运行时悄悄连接默认业务数据库。
    from backend.database import engine
    connection = redis_connection()
    hour = int(os.environ.get("NEWS_DAILY_HOUR", "8"))
    if not 0 <= hour <= 23 or int(os.environ.get("NEWS_INITIAL_DAYS", "7")) < 1 or int(os.environ.get("NEWS_MAX_PAGES", "100")) < 1:
        parser.error("采集窗口/页数必须为正数，小时范围 0–23")
    if args.command == "worker":
        from rq import Worker
        run_worker(Worker)
    elif args.command == "schedule":
        schedule_forever(engine, connection, hour, os.environ.get("NEWS_TIMEZONE", "Asia/Shanghai"))
    else:
        success = True
        for source in SOURCES if args.source == "all" else (args.source,):
            try:
                success = run_job(source) and success
            except Exception as exc:
                logging.error("news source=%s exception=%s", source, type(exc).__name__)
                success = False
        raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
