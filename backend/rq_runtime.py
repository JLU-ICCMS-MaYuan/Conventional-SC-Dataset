"""RQ Worker 生命周期：空闲退出或 Redis 短暂故障后自动重建。"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from redis.exceptions import RedisError


def run_worker_forever(
    create_worker: Callable[[], Any],
    work: Callable[[Any], Any],
    *,
    label: str,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """持续运行 RQ Worker；显式停止时返回，异常退出时重建连接。"""
    log = logging.getLogger(__name__)
    while True:
        worker = None
        try:
            worker = create_worker()
            work(worker)
        except RedisError:
            log.warning("%s redis disconnected; reconnecting", label)
            sleep(5)
            continue
        if worker is not None and (
            getattr(worker, "_stop_requested", False)
            or getattr(worker, "_shutdown_requested_date", None) is not None
        ):
            return
        log.warning("%s stopped unexpectedly; restarting", label)
        sleep(5)
