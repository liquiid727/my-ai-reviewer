"""Context-local correlation fields for one resume worker execution."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_context: ContextVar[dict[str, Any]] = ContextVar("resume_observability_context", default={})


@contextmanager
def bind_resume_context(**values: Any) -> Iterator[None]:
    current = {**_context.get(), **{key: value for key, value in values.items() if value is not None}}
    token = _context.set(current)
    try:
        yield
    finally:
        _context.reset(token)


def resume_context() -> dict[str, Any]:
    return dict(_context.get())
