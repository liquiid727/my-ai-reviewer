"""数据库连接配置 —— 创建异步引擎、会话工厂和 ORM 基类。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

settings = get_settings()

# 创建异步数据库引擎（支持连接池健康检查）
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # DEBUG 模式下打印 SQL 语句
    pool_pre_ping=True,        # 每次从连接池取连接前先 ping 一下
)

# 异步会话工厂
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,    # 提交后不自动过期属性，避免懒加载问题
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 声明式基类。"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取一个数据库会话，请求结束后自动关闭。"""
    async with async_session_factory() as session:
        yield session
