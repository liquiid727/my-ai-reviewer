"""LangGraph checkpoint 持久化 —— 使用 PostgreSQL 存储图执行状态。"""

import asyncio
from contextlib import AsyncExitStack

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import get_settings

_checkpointer: AsyncPostgresSaver | None = None
# from_conn_string 是异步上下文管理器，用 ExitStack 持有以保持单例连接不被关闭
_exit_stack: AsyncExitStack | None = None
_initialization_lock = asyncio.Lock()


def get_checkpoint_conn_string() -> str:
    """获取 psycopg3 格式的数据库连接字符串（LangGraph 要求 psycopg3，非 asyncpg）。"""
    settings = get_settings()
    url = settings.DATABASE_URL
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return url


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取单例 LangGraph checkpoint 存储，避免重复创建连接。"""
    global _checkpointer, _exit_stack
    if _checkpointer is None:
        async with _initialization_lock:
            if _checkpointer is None:
                conn_string = get_checkpoint_conn_string()
                exit_stack = AsyncExitStack()
                try:
                    checkpointer = await exit_stack.enter_async_context(
                        AsyncPostgresSaver.from_conn_string(conn_string)
                    )
                    await checkpointer.setup()
                except Exception:
                    await exit_stack.aclose()
                    raise
                _exit_stack = exit_stack
                _checkpointer = checkpointer
    return _checkpointer
