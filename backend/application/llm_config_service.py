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
            try:
                api_key = get_encryptor().decrypt(stored.api_key_encrypted)
            except Exception as exc:
                return {
                    "success": False,
                    "error": _friendly_connection_error(exc),
                }
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


async def _run_connection_test(
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
) -> dict[str, object]:
    """向 LLM 提供商发送最小请求或列出可用模型，验证连通性。

    OpenAI 兼容渠道优先 ``models.list`` 探测模型清单；若渠道未实现该接口，
    再回退到一次最小 chat 请求，确保“测试连接”与“加载模型列表”都能工作。
    """
    if provider == "anthropic":
        try:
            from anthropic import AsyncAnthropic

            # 客户端构造也可能因代理依赖缺失而失败，必须纳入 try
            anthropic_client = AsyncAnthropic(api_key=api_key, base_url=base_url)
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
            return {"success": False, "error": _friendly_connection_error(exc)}

    try:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
        # 1) 优先拉取模型列表，供前端下拉/点选
        try:
            models_response = await asyncio.wait_for(
                openai_client.models.list(),
                timeout=15,
            )
            model_ids = sorted(
                {m.id for m in models_response.data if getattr(m, "id", None)},
                key=str.lower,
            )
            # 当前填写的模型优先展示，其余按字母序
            if model_name and model_name not in model_ids:
                model_ids = [model_name, *model_ids]
            elif model_name in model_ids:
                model_ids = [model_name, *[m for m in model_ids if m != model_name]]
            return {"success": True, "models": model_ids[:100]}
        except Exception as list_exc:
            # 2) 部分中转站未实现 /v1/models，回退到最小 chat 验证 Key + 模型
            try:
                await asyncio.wait_for(
                    openai_client.chat.completions.create(
                        model=model_name,
                        max_tokens=1,
                        messages=[{"role": "user", "content": "hi"}],
                    ),
                    timeout=15,
                )
                return {
                    "success": True,
                    "models": [model_name],
                    "warning": (
                        "models.list unavailable; verified via chat.completions instead: "
                        f"{_friendly_connection_error(list_exc)}"
                    ),
                }
            except Exception as chat_exc:
                # 两个路径都失败时，优先返回 chat 错误（与所选模型更相关）
                return {"success": False, "error": _friendly_connection_error(chat_exc)}
    except Exception as exc:
        return {"success": False, "error": _friendly_connection_error(exc)}
