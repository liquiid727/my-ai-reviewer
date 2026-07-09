"""通用仓储层 —— 提供基础的 CRUD 操作，减少重复代码。"""

import uuid
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT]:
    """通用仓储基类，封装常用的数据库操作。"""

    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    async def create(self, **kwargs: Any) -> ModelT:
        """创建新记录并返回。"""
        instance = self._model_class(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        """根据 ID 查询单条记录。"""
        stmt = select(self._model_class).where(self._model_class.id == id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelT | None:
        """根据 ID 更新记录的指定字段。"""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance
