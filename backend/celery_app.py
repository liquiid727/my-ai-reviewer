"""Celery 应用实例 —— 配置异步任务队列的 broker 和 result backend。"""

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from backend.config import get_settings
from backend.tasks.async_runtime import initialize_worker_process, shutdown_worker_process

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
        "backend.tasks.plan_tasks",
        "backend.tasks.match_tasks",
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


@worker_process_init.connect  # type: ignore[untyped-decorator]
def _initialize_async_runtime(**_: object) -> None:
    """Reset inherited pool state before a prefork worker child runs a task."""
    initialize_worker_process()


@worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def _shutdown_async_runtime(**_: object) -> None:
    """Release the worker child's async connections during graceful shutdown."""
    shutdown_worker_process()
