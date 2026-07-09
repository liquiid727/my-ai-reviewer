"""Alembic 数据库迁移环境配置 —— 支持离线和在线（异步）两种迁移模式。"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_settings
from backend.infrastructure.db.database import Base
from backend.infrastructure.db import models  # noqa: F401 — 注册所有 ORM 模型以便自动生成迁移

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标元数据（Alembic 据此自动检测模型变更）
target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """离线模式迁移：生成 SQL 脚本但不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    """在数据库连接上执行迁移。"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """在线模式迁移：使用异步引擎连接数据库并执行迁移。"""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
