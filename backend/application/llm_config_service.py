import asyncio
import uuid

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
    stmt = select(LLMConfigModel).order_by(LLMConfigModel.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_config(
    session: AsyncSession,
    config_id: uuid.UUID,
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    base_url: str | None = ...,  # type: ignore[assignment]
) -> LLMConfigModel | None:
    # base_url default is ... (sentinel) to distinguish "not provided" from "set to None"
    config = await session.get(LLMConfigModel, config_id)
    if config is None:
        return None
    if provider is not None:
        config.provider = provider
    if api_key is not None:
        config.api_key_encrypted = get_encryptor().encrypt(api_key)
    if model_name is not None:
        config.model_name = model_name
    if base_url is not ...:
        config.base_url = base_url
    await session.commit()
    await session.refresh(config)
    return config


async def delete_config(session: AsyncSession, config_id: uuid.UUID) -> bool:
    config = await session.get(LLMConfigModel, config_id)
    if config is None:
        return False
    await session.delete(config)
    await session.commit()
    return True


async def test_connection(
    provider: str,
    api_key: str,
    model_name: str,
    base_url: str | None = None,
) -> dict[str, object]:
    """Test LLM provider connection by listing models or sending a minimal request."""
    if provider == "anthropic":
        from anthropic import AsyncAnthropic

        anthropic_client = AsyncAnthropic(api_key=api_key)
        try:
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
            models_response = await asyncio.wait_for(
                openai_client.models.list(),
                timeout=15,
            )
            model_ids = [m.id for m in models_response.data[:20]]
            return {"success": True, "models": model_ids}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
