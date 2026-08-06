"""LLM 配置服务层 —— 提供 LLM 配置的增删改查和连通性测试。"""

import uuid
from datetime import UTC, datetime
from types import EllipsisType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.llm.multimodal import LLMCapabilities, capabilities_from_dict, infer_transport
from backend.infrastructure.crypto.encryption import APIKeyEncryptor, get_encryptor
from backend.infrastructure.db.models import LLMConfigModel
from backend.infrastructure.llm.connection_probe import run_connection_test


async def create_config(
    session: AsyncSession,
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
    capabilities: dict[str, object] | None = None,
) -> LLMConfigModel:
    """创建新的 LLM 配置，API Key 加密后存储。"""
    explicit_capabilities = capabilities_from_dict(capabilities or {}, provider=provider)
    config = LLMConfigModel(
        provider=provider,
        api_key_encrypted=get_encryptor().encrypt(api_key),
        model_name=model_name,
        base_url=base_url,
        capabilities=explicit_capabilities.model_dump(mode="json"),
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
        select(LLMConfigModel.id).where(LLMConfigModel.is_active.is_(True), LLMConfigModel.verified.is_(True)).limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def has_verified_vision_config(session: AsyncSession) -> bool:
    """Return whether active verified config explicitly supports Vision."""
    config = await get_active_verified_config(session)
    if config is None:
        return False
    capabilities = capabilities_from_dict(getattr(config, "capabilities", None) or {}, provider=config.provider)
    return capabilities.supports_vision and capabilities.verified_at is not None


async def get_active_verified_config(session: AsyncSession) -> LLMConfigModel | None:
    """返回当前实际用于 AI 调用的已激活且已验证配置。"""
    stmt = (
        select(LLMConfigModel)
        .where(LLMConfigModel.is_active.is_(True), LLMConfigModel.verified.is_(True))
        .order_by(LLMConfigModel.updated_at.desc(), LLMConfigModel.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_config(
    session: AsyncSession,
    config_id: uuid.UUID,
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None | EllipsisType = ...,
    capabilities: dict[str, object] | None = None,
) -> LLMConfigModel | None:
    """更新指定的 LLM 配置，只修改传入的字段。

    base_url 默认值为 ... (哨兵值)，用于区分"未传入"和"显式设为 None"。
    """
    config = await session.get(LLMConfigModel, config_id)
    if config is None:
        return None
    # 关键字段变更时重置已验证状态，需重新测试（verified 不设过期）
    key_field_changed = provider is not None or api_key is not None or model_name is not None
    if provider is not None:
        config.provider = provider
    if api_key is not None:
        config.api_key_encrypted = get_encryptor().encrypt(api_key)
    if model_name is not None:
        config.model_name = model_name
    if base_url is not ...:
        config.base_url = base_url
        key_field_changed = True
    if capabilities is not None:
        config.capabilities = capabilities_from_dict(capabilities, provider=config.provider).model_dump(mode="json")
        config.capabilities_verified_at = None
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
            try:
                api_key = get_encryptor().decrypt(stored.api_key_encrypted)
            except Exception as exc:
                return {
                    "success": False,
                    "error": _friendly_connection_error(exc),
                }
    if not api_key:
        return {"success": False, "error": "API key is required"}

    result = await run_connection_test(provider, api_key, model_name, base_url)
    capabilities = _capabilities_from_test_result(provider, result)
    result["capabilities"] = capabilities.model_dump(mode="json")
    if session is not None and config_id is not None:
        config = await session.get(LLMConfigModel, config_id)
        if config is not None:
            success = bool(result["success"])
            config.verified = success
            if success:
                verified_at = datetime.now(UTC)
                config.last_verified_at = verified_at
                persisted = capabilities_from_dict(
                    getattr(config, "capabilities", None) or {}, provider=config.provider
                )
                capabilities = persisted.model_copy(update={"verified_at": verified_at})
                config.capabilities = capabilities.model_dump(mode="json")
                config.capabilities_verified_at = verified_at
                result["capabilities"] = config.capabilities
            else:
                config.capabilities_verified_at = None
            await session.commit()
    return result


def _capabilities_from_test_result(provider: str, result: dict[str, object]) -> LLMCapabilities:
    transport = infer_transport(provider)
    if not bool(result.get("success")):
        return LLMCapabilities.text_defaults(transport=transport)
    declared = result.get("capabilities")
    if isinstance(declared, dict):
        return capabilities_from_dict(declared, provider=provider)
    return LLMCapabilities(
        supports_text=True,
        supports_structured_output=True,
        supports_vision=False,
        max_images=None,
        max_image_bytes=None,
        transport=transport,
        verified_at=datetime.now(UTC),
    )


def _friendly_connection_error(exc: BaseException) -> str:
    """将底层 SDK/网络异常整理为可读错误，避免前端只看到笼统失败。"""
    message = str(exc).strip() or type(exc).__name__
    lowered = message.lower()
    if "socksio" in lowered or "socks proxy" in lowered:
        return (
            "当前环境启用了 SOCKS 代理，但缺少 socksio 依赖。"
            "请执行 `uv add 'httpx[socks]'` 后重启后端，或取消 ALL_PROXY/HTTPS_PROXY。"
        )
    if "encryption_key" in lowered:
        return "ENCRYPTION_KEY 未配置，无法读写已保存的 API Key。请先在 .env 中设置后重启后端。"
    # Fernet 解密失败：常见于更换 ENCRYPTION_KEY 后仍使用旧密文
    if type(exc).__name__ == "InvalidToken" or "invalidtoken" in lowered:
        return (
            "已保存的 API Key 无法解密（ENCRYPTION_KEY 已变更或与写入时不一致）。"
            "请删除该配置后重新填写 API Key 保存，或在测试时重新输入 API Key。"
        )
    return message


def serialize_config(config: LLMConfigModel) -> dict[str, object]:
    """Serialize an LLM config for API responses with a masked API key."""
    try:
        decrypted = get_encryptor().decrypt(config.api_key_encrypted)
        masked_key = APIKeyEncryptor.mask(decrypted)
    except Exception:
        masked_key = "***"
    return {
        "id": str(config.id),
        "provider": config.provider,
        "api_key": masked_key,
        "model_name": config.model_name,
        "base_url": config.base_url,
        "is_active": config.is_active,
        "verified": config.verified,
        "last_verified_at": (config.last_verified_at.isoformat() if config.last_verified_at else None),
        "capabilities": capabilities_from_dict(
            getattr(config, "capabilities", None) or {}, provider=config.provider
        ).model_dump(mode="json"),
        "capabilities_verified_at": (
            config.capabilities_verified_at.isoformat() if config.capabilities_verified_at is not None else None
        ),
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }
