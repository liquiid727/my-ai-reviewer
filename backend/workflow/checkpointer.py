"""LangGraph checkpoint 持久化 —— 使用 PostgreSQL 存储图执行状态。"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import get_settings

_checkpointer: AsyncPostgresSaver | None = None


def get_checkpoint_conn_string() -> str:
    """获取 psycopg3 格式的数据库连接字符串（LangGraph 要求 psycopg3，非 asyncpg）。"""
    settings = get_settings()
    url = settings.DATABASE_URL
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return url


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取单例 LangGraph checkpoint 存储，避免重复创建连接。"""
    global _checkpointer
    if _checkpointer is None:
        conn_string = get_checkpoint_conn_string()
        _checkpointer = AsyncPostgresSaver.from_conn_string(conn_string)
        await _checkpointer.setup()
    return _checkpointer
