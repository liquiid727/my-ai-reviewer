"""Celery 应用实例 —— 配置异步任务队列的 broker 和 result backend。"""

from celery import Celery

from backend.config import get_settings

settings = get_settings()

# 创建 Celery 实例，使用 Redis 作为消息中间件和结果存储
# include 显式导入任务模块，确保 worker 启动时注册所有任务
celery = Celery(
    "ai_interview",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.resume_tasks",
        "backend.tasks.interview_tasks",
        "backend.tasks.jd_tasks",
        "backend.tasks.jd_match_tasks",
        "backend.tasks.plan_tasks",
        "backend.tasks.resume_watchdog",
    ],
)

# 序列化与时区配置
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "resume-processing-watchdog": {
            "task": "tasks.resume_watchdog",
            "schedule": 30.0,
            "args": (100,),
        },
    },
)
