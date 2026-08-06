"""Shared synchronous bridge for async Celery task implementations."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

_T = TypeVar("_T")
_loop_local = threading.local()


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine on one loop per worker thread and process.

    Celery's prefork pool can inherit module state from its parent process,
    while different task modules may otherwise create separate loops in the
    same worker.  The PID guard discards an inherited loop after fork; the
    shared helper keeps all task modules on the same loop afterwards.
    """

    process_id = os.getpid()
    loop = getattr(_loop_local, "loop", None)
    loop_process_id = getattr(_loop_local, "process_id", None)
    if loop is None or loop.is_closed() or loop_process_id != process_id:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop_local.loop = loop
        _loop_local.process_id = process_id
    return loop.run_until_complete(coro)


__all__ = ["run_async"]
