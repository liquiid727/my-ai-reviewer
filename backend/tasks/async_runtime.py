"""Worker-local asyncio runtime for synchronous Celery task entry points."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine
from typing import Any, TypeVar

from backend.infrastructure.db.database import async_engine

_T = TypeVar("_T")
_loop: asyncio.AbstractEventLoop | None = None
_loop_process_id: int | None = None


def _worker_loop() -> asyncio.AbstractEventLoop:
    """Return the sole event loop owned by the current Celery child process."""
    global _loop, _loop_process_id

    process_id = os.getpid()
    if _loop is None or _loop.is_closed() or _loop_process_id != process_id:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop_process_id = process_id
    return _loop


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run async worker work on the single loop associated with this child."""
    loop = _worker_loop()
    if loop.is_running():
        coro.close()
        raise RuntimeError("Celery async runtime cannot be re-entered")
    return loop.run_until_complete(coro)


def initialize_worker_process() -> None:
    """Discard parent-process connections before a prefork child accepts work."""
    global _loop, _loop_process_id

    if _loop is not None and not _loop.is_running() and not _loop.is_closed():
        _loop.close()
    _loop = None
    _loop_process_id = None
    # Do not close inherited file descriptors from the parent process. The child
    # receives a fresh pool and all future asyncpg connections bind to its loop.
    async_engine.sync_engine.dispose(close=False)


def shutdown_worker_process() -> None:
    """Close this child process's async connections and event loop."""
    global _loop, _loop_process_id

    loop = _loop
    try:
        if loop is None or loop.is_closed():
            async_engine.sync_engine.dispose(close=False)
            return
        loop.run_until_complete(async_engine.dispose())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
    finally:
        _loop = None
        _loop_process_id = None
