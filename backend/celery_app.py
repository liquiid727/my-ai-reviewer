"""Celery 应用实例 —— 配置异步任务队列的 broker 和 result backend。"""

from celery import Celery

from backend.config import get_settings

settings = get_settings()

# 创建 Celery 实例，使用 Redis 作为消息中间件和结果存储
celery = Celery(
    "ai_interview",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 序列化与时区配置
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
