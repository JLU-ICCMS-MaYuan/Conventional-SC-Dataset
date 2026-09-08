"""启动可配置数量的 RQ 上传 Worker，并由第一个进程负责延迟任务调度。"""

from __future__ import annotations

import multiprocessing
import signal
from typing import NoReturn

from redis import Redis
from rq import Worker

from backend.ingest.upload_tasks import QUEUE_NAME, handle_upload_job_failure
from backend.rag.config import settings
from backend.rq_runtime import run_worker_forever


def _run_worker(with_scheduler: bool) -> None:
    run_worker_forever(
        lambda: Worker(
            [QUEUE_NAME],
            connection=Redis.from_url(settings.redis_url),
            exception_handlers=[handle_upload_job_failure],
        ),
        lambda worker: worker.work(with_scheduler=with_scheduler),
        label="upload worker",
    )


def main() -> NoReturn:
    count = max(1, settings.upload_llm_concurrency)
    processes = [
        multiprocessing.Process(target=_run_worker, args=(index == 0,))
        for index in range(count)
    ]
    for process in processes:
        process.start()

    def stop(_signum, _frame) -> None:
        for process in processes:
            if process.is_alive():
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for process in processes:
        process.join()
    raise SystemExit(max((process.exitcode or 0) for process in processes))


if __name__ == "__main__":
    main()
