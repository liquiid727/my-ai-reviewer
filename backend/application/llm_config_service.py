"""LLM 配置服务层 —— 提供 LLM 配置的增删改查和连通性测试。"""

import asyncio
import uuid
from datetime import UTC, datetime
from types import EllipsisType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.crypto.encryption import get_encryptor
from backend.infrastructure.db.models import LLMConfigModel


async def create_config(
    session: AsyncSession,
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
) -> LLMConfigModel:
    """创建新的 LLM 配置，API Key 加密后存储。"""
    config = LLMConfigModel(
        provider=provider,
        api_key_encrypted=get_encryptor().encrypt(api_key),
        model_name=model_name,
        base_url=base_url,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def list_configs(session: AsyncSession) -> list[LLMConfigModel]:
    """查询所有 LLM 配置，按创建时间倒序排列。"""
    stmt = select(LLMConfigModel).order_by(LLMConfigModel.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def has_verified_config(session: AsyncSession) -> bool:
    """是否存在"已激活且已验证"的 LLM 配置（上传门禁的判定依据）。"""
    stmt = (
        select(LLMConfigModel.id)
        .where(LLMConfigModel.is_active.is_(True), LLMConfigModel.verified.is_(True))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def update_config(
    session: AsyncSession,
    config_id: uuid.UUID,
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None | EllipsisType = ...,
) -> LLMConfigModel | None:
    """更新指定的 LLM 配置，只修改传入的字段。

    base_url 默认值为 ... (哨兵值)，用于区分"未传入"和"显式设为 None"。
    """
    config = await session.get(LLMConfigModel, config_id)
    if config is None:
        return None
    # 关键字段变更时重置已验证状态，需重新测试（verified 不设过期）
    key_field_changed = (
        provider is not None
        or api_key is not None
        or model_name is not None
    )
    if provider is not None:
        config.provider = provider
    if api_key is not None:
        config.api_key_encrypted = get_encryptor().encrypt(api_key)
    if model_name is not None:
        config.model_name = model_name
    if base_url is not ...:
        config.base_url = base_url
        key_field_changed = True
    if key_field_changed:
        config.verified = False
    await session.commit()
    await session.refresh(config)
    return config


async def delete_config(session: AsyncSession, config_id: uuid.UUID) -> bool:
    """删除指定的 LLM 配置，返回是否成功。"""
    config = await session.get(LLMConfigModel, config_id)
    if config is None:
        return False
    await session.delete(config)
    await session.commit()
    return True


async def test_connection(
    provider: str,
    api_key: str | None,
    model_name: str,
    base_url: str | None = None,
    *,
    session: AsyncSession | None = None,
    config_id: uuid.UUID | None = None,
) -> dict[str, object]:
    """测试 LLM 提供商连通性。

    传入 ``session`` 与 ``config_id`` 且命中已保存配置时，根据测试结果落库：
    测试通过则置 ``verified=true`` 并更新 ``last_verified_at``；测试失败置
    ``verified=false``。不传 ``config_id`` 时仅测试不落库。

    ``api_key`` 为空且命中已保存配置时，自动解密使用存储的 Key（前端
    只持有脱敏 Key，验证已保存配置时无需重新输入）。
    """
    if not api_key and session is not None and config_id is not None:
        stored = await session.get(LLMConfigModel, config_id)
        if stored is not None:
            api_key = get_encryptor().decrypt(stored.api_key_encrypted)
    if not api_key:
        return {"success": False, "error": "API key is required"}

    result = await _run_connection_test(provider, api_key, model_name, base_url)
    if session is not None and config_id is not None:
        config = await session.get(LLMConfigModel, config_id)
        if config is not None:
            success = bool(result["success"])
            config.verified = success
            if success:
                config.last_verified_at = datetime.now(UTC)
            await session.commit()
    return result


async def _run_connection_test(
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
) -> dict[str, object]:
    """向 LLM 提供商发送最小请求或列出可用模型，验证连通性。"""
    if provider == "anthropic":
        from anthropic import AsyncAnthropic

        anthropic_client = AsyncAnthropic(api_key=api_key)
        try:
            # 发送一条最小消息来验证 API Key 和模型是否有效
            await asyncio.wait_for(
                anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                ),
                timeout=15,
            )
            return {"success": True, "models": [model_name]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    else:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        try:
            # 通过列出可用模型来验证连通性
            models_response = await asyncio.wait_for(
                openai_client.models.list(),
                timeout=15,
            )
            model_ids = [m.id for m in models_response.data[:20]]
            return {"success": True, "models": model_ids}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
