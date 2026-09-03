"""固定资讯队列和可恢复的日调度；不导入上传任务。"""
from datetime import datetime, timedelta, timezone
import logging
import os
import time
from zoneinfo import ZoneInfo

from redis import Redis
from redis.exceptions import LockError
from rq import Queue
from rq.job import JobStatus
from sqlalchemy.orm import Session

from .domain import CollectionError, SOURCES, parse_time
from .models import NewsFeedSource

QUEUE_NAME = "scwiki-news"
JOB_TIMEOUT = 900
ACTIVE = {JobStatus.QUEUED, JobStatus.STARTED, JobStatus.DEFERRED, JobStatus.SCHEDULED}


def scheduled_at(now, hour=8, zone="Asia/Shanghai"):
    local = now.astimezone(ZoneInfo(zone))
    result = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if result > local:
        result -= timedelta(days=1)
    return result.astimezone(timezone.utc)


def due(state, cutoff, now):
    if state is None:
        return True
    if state.status == "running" and state.last_started_at:
        return now - parse_time(state.last_started_at) > timedelta(seconds=JOB_TIMEOUT + 100)
    if state.status == "failed" and state.last_finished_at:
        return now - parse_time(state.last_finished_at) >= timedelta(hours=1)
    if state.last_success_at and parse_time(state.last_success_at) >= cutoff:
        return False
    return True


def redis_connection():
    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL 未设置，资讯进程拒绝使用隐式默认连接")
    # RQ Worker 通过 PubSub 长时间阻塞读取；短 socket_timeout 会让空闲队列错误退出。
    return Redis.from_url(url, socket_timeout=None, socket_connect_timeout=10)


def enqueue_due(engine, connection, now=None, hour=8, zone="Asia/Shanghai"):
    now = now or datetime.now(timezone.utc)
    cutoff = scheduled_at(now, hour, zone)
    lock = connection.lock("scwiki-news:schedule-lock", timeout=30, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return []
    try:
        queue = Queue(QUEUE_NAME, connection=connection, default_timeout=JOB_TIMEOUT)
        queued = []
        with Session(engine) as db:
            for source in SOURCES:
                if not due(db.get(NewsFeedSource, source), cutoff, now):
                    continue
                job_id = "scwiki-news-" + source
                previous = queue.fetch_job(job_id)
                if previous and previous.get_status(refresh=True) in ACTIVE:
                    # RQ worker 的维护循环负责移除死亡 worker 遗留的 started 作业。
                    continue
                if previous:
                    previous.delete()
                queue.enqueue("backend.news.scheduler.run_job", source, job_id=job_id,
                              job_timeout=JOB_TIMEOUT, result_ttl=86400, failure_ttl=86400)
                queued.append(source)
        return queued
    finally:
        try:
            lock.release()
        except LockError:
            logging.getLogger(__name__).warning("news schedule lock expired")


def run_job(source):
    from backend.database import engine
    from .service import collect_source
    from .sources import Sources

    # RQ 在子进程中运行，不复用父进程已有的数据库连接。
    engine.dispose(close=False)
    connection = redis_connection()
    lock = connection.lock("scwiki-news:collection-lock", timeout=JOB_TIMEOUT + 100, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        # 没有取得锁不发请求，调度将在本作业结束后重试。
        raise CollectionError("collection_busy")
    transport = None
    try:
        started = time.monotonic()
        def guard():
            if time.monotonic() - started > JOB_TIMEOUT - 30 or not lock.owned():
                raise CollectionError("collection_timeout")
        sources = Sources(max_pages=int(os.environ.get("NEWS_MAX_PAGES", "100")),
                          contact=os.environ.get("NEWS_CONTACT_EMAIL", ""))
        transport = sources.transport
        transport.guard = guard
        return collect_source(engine, source, sources, initial_days=int(os.environ.get("NEWS_INITIAL_DAYS", "7")),
                              before_commit=guard)
    finally:
        if transport:
            transport.close()
        try:
            lock.release()
        except LockError:
            logging.getLogger(__name__).warning("news collection lock expired")


def schedule_forever(engine, connection, hour=8, zone="Asia/Shanghai"):
    while True:
        try:
            enqueue_due(engine, connection, hour=hour, zone=zone)
        except Exception as exc:
            logging.getLogger(__name__).error("news scheduler failed: %s", type(exc).__name__)
        time.sleep(60)
