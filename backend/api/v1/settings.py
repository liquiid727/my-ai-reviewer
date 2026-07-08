import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application import llm_config_service
from backend.infrastructure.crypto.encryption import APIKeyEncryptor, get_encryptor
from backend.infrastructure.db.database import get_db
from backend.infrastructure.db.models import LLMConfigModel

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str
    model_name: str
    base_url: str | None = None


class LLMConfigUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    base_url: str | None = None


class LLMConfigTestRequest(BaseModel):
    provider: str
    api_key: str
    model_name: str
    base_url: str | None = None


@router.post("/llm", response_model=APIResponse)
async def create_llm_config(
    body: LLMConfigCreate,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    config = await llm_config_service.create_config(
        session, body.provider, body.api_key, body.model_name, body.base_url,
    )
    return APIResponse(data=_serialize(config))


@router.get("/llm", response_model=APIResponse)
async def list_llm_configs(
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    configs = await llm_config_service.list_configs(session)
    return APIResponse(data=[_serialize(c) for c in configs])


@router.put("/llm/{config_id}", response_model=APIResponse)
async def update_llm_config(
    config_id: uuid.UUID,
    body: LLMConfigUpdate,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    kwargs = body.model_dump(exclude_unset=True)
    config = await llm_config_service.update_config(session, config_id, **kwargs)
    if config is None:
        return APIResponse(code=404, message="Config not found")
    return APIResponse(data=_serialize(config))


@router.delete("/llm/{config_id}", response_model=APIResponse)
async def delete_llm_config(
    config_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    deleted = await llm_config_service.delete_config(session, config_id)
    if not deleted:
        return APIResponse(code=404, message="Config not found")
    return APIResponse()


@router.post("/llm/test", response_model=APIResponse)
async def test_llm_connection(body: LLMConfigTestRequest) -> APIResponse:
    result = await llm_config_service.test_connection(
        body.provider, body.api_key, body.model_name, body.base_url,
    )
    return APIResponse(data=result)


def _serialize(config: LLMConfigModel) -> dict[str, object]:
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
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }
