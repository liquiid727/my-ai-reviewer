"""全局配置 —— 使用 pydantic-settings 从 .env 文件和环境变量中加载配置项。"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── 应用基础 ─────────────────────────────────
    APP_NAME: str = "AI Interview Platform"
    DEBUG: bool = False

    # ── 数据库（PostgreSQL + asyncpg） ───────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/ai_interview"

    # ── Redis（缓存 & 会话） ─────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── MinIO / S3 对象存储 ──────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_RESUMES: str = "resumes"
    MINIO_USE_SSL: bool = False

    # ── CORS 跨域白名单 ─────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Celery 异步任务队列 ──────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── 加密密钥（用于 API Key 加密存储） ────────
    ENCRYPTION_KEY: str = ""

    # ── LLM 大模型配置 ──────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4o"


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，只加载一次）。"""
    return Settings()
