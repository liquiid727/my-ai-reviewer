"""Worker-local asyncio runtime for synchronous Celery task entry points.

One event loop per worker thread and process. Celery's prefork pool can
inherit module state from its parent process, and different task modules may
otherwise create separate loops in the same worker; the PID guard discards an
inherited loop after fork, and the shared helper keeps all task modules on the
same loop afterwards.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

from backend.infrastructure.db.database import async_engine

_T = TypeVar("_T")
_loop_local = threading.local()


def _worker_loop() -> asyncio.AbstractEventLoop:
    """Return the sole event loop owned by the current worker thread/process."""
    process_id = os.getpid()
    loop = getattr(_loop_local, "loop", None)
    loop_process_id = getattr(_loop_local, "process_id", None)
    if loop is None or loop.is_closed() or loop_process_id != process_id:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop_local.loop = loop
        _loop_local.process_id = process_id
    return loop


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run async worker work on the single loop associated with this thread."""
    loop = _worker_loop()
    if loop.is_running():
        coro.close()
        raise RuntimeError("Celery async runtime cannot be re-entered")
    return loop.run_until_complete(coro)


def initialize_worker_process() -> None:
    """Discard parent-process connections before a prefork child accepts work."""
    loop = getattr(_loop_local, "loop", None)
    if loop is not None and not loop.is_running() and not loop.is_closed():
        loop.close()
    _loop_local.loop = None
    _loop_local.process_id = None
    # Do not close inherited file descriptors from the parent process. The child
    # receives a fresh pool and all future asyncpg connections bind to its loop.
    async_engine.sync_engine.dispose(close=False)


def shutdown_worker_process() -> None:
    """Close this child process's async connections and event loop."""
    loop = getattr(_loop_local, "loop", None)
    try:
        if loop is None or loop.is_closed():
            async_engine.sync_engine.dispose(close=False)
            return
        loop.run_until_complete(async_engine.dispose())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
    finally:
        _loop_local.loop = None
        _loop_local.process_id = None


__all__ = ["run_async", "initialize_worker_process", "shutdown_worker_process"]
