"""Periodic task scheduler — re-enqueues entries from `timer_task_config`."""

from __future__ import annotations

import threading
from typing import Any

from app.automation.config import timer_task_config
from app.core.constants import READY
from app.core.logging import logger
from app.core.tasks import sync_task_manager


_timers: dict[str, threading.Timer] = {}


def _enqueue_periodic(task_id: str, content: dict[str, Any]) -> None:
    try:
        if content.get("cache", False):
            ok = sync_task_manager.update_task(task_id, status=READY)
            if not ok:
                sync_task_manager.add_task(
                    task_id,
                    content.get("client_id"),
                    content.get("commands", []),
                    READY,
                    is_chunked=bool(content.get("chunked", False)),
                )
        else:
            sync_task_manager.add_task(
                task_id,
                content.get("client_id"),
                content.get("commands", []),
                READY,
                is_chunked=bool(content.get("chunked", False)),
            )
    except Exception:
        logger.exception("Scheduler failed to enqueue %s", task_id)

    interval = int(content.get("interval", 30))
    timer = threading.Timer(interval, _enqueue_periodic, args=[task_id, content])
    _timers[task_id] = timer
    timer.start()


def start_scheduler() -> None:
    for task_id, content in timer_task_config.items():
        interval = int(content.get("interval", 30))
        timer = threading.Timer(interval, _enqueue_periodic, args=[task_id, content])
        _timers[task_id] = timer
        timer.start()


def stop_scheduler() -> None:
    for timer in _timers.values():
        try:
            timer.cancel()
        except Exception:
            pass
    _timers.clear()
