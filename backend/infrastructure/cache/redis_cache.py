"""Redis 缓存适配器：提供字节与 JSON 两类短期缓存能力。

纯缓存语义，fail-open：Redis 不可用时读视为未命中、写静默跳过，
绝不影响主流程；业务状态一律以 PostgreSQL 为准。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from backend.config import get_settings

logger = logging.getLogger(__name__)

_client: Redis | None = None


def get_redis_client() -> Redis:
    """惰性创建全局 Redis 客户端单例（decode_responses=False，按字节读写）。"""
    global _client
    if _client is None:
        _client = Redis.from_url(get_settings().REDIS_URL, decode_responses=False)
    return _client


async def cache_get_bytes(key: str) -> bytes | None:
    """读取字节缓存；未命中或 Redis 异常时返回 None。"""
    try:
        value = await get_redis_client().get(key)
    except Exception:
        logger.warning("Redis cache get failed for %s; treating as miss", key, exc_info=True)
        return None
    if value is None:
        return None
    # decode_responses=False 时实际返回 bytes；对 stub 声明的宽类型做防御性归一
    return value if isinstance(value, bytes) else value.encode("utf-8")


async def cache_set_bytes(key: str, value: bytes, ttl_seconds: int) -> None:
    """写入字节缓存并设置 TTL；Redis 异常时静默跳过。"""
    try:
        await get_redis_client().set(key, value, ex=ttl_seconds)
    except Exception:
        logger.warning("Redis cache set failed for %s; skipping", key, exc_info=True)


async def cache_get_json(key: str) -> dict[str, Any] | None:
    """读取 JSON 缓存；未命中、解析失败或 Redis 异常时返回 None。"""
    raw = await cache_get_bytes(key)
    if raw is None:
        return None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Redis cache value for %s is not valid JSON; treating as miss", key)
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


async def cache_set_json(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
    """写入 JSON 缓存并设置 TTL；Redis 异常时静默跳过。"""
    await cache_set_bytes(key, json.dumps(value, ensure_ascii=False).encode("utf-8"), ttl_seconds)
