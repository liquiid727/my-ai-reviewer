"""LLM 配置管理接口 —— 新增、查看、修改、删除和测试 LLM 提供商配置。"""

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
    """创建 LLM 配置的请求体。"""
    provider: str           # 提供商名称（openai / anthropic / deepseek）
    api_key: str            # API 密钥（明文传入，存储时加密）
    model_name: str         # 模型名称（如 gpt-4o）
    base_url: str | None = None  # 自定义 API 地址（可选）


class LLMConfigUpdate(BaseModel):
    """更新 LLM 配置的请求体（所有字段可选，只更新传入的字段）。"""
    provider: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    base_url: str | None = None


class LLMConfigTestRequest(BaseModel):
    """测试 LLM 连通性的请求体。"""
    provider: str
    api_key: str
    model_name: str
    base_url: str | None = None


@router.post("/llm", response_model=APIResponse)
async def create_llm_config(
    body: LLMConfigCreate,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """新增一条 LLM 配置。"""
    config = await llm_config_service.create_config(
        session, body.provider, body.api_key, body.model_name, body.base_url,
    )
    return APIResponse(data=_serialize(config))


@router.get("/llm", response_model=APIResponse)
async def list_llm_configs(
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """列出所有 LLM 配置（API Key 脱敏显示）。"""
    configs = await llm_config_service.list_configs(session)
    return APIResponse(data=[_serialize(c) for c in configs])


@router.put("/llm/{config_id}", response_model=APIResponse)
async def update_llm_config(
    config_id: uuid.UUID,
    body: LLMConfigUpdate,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新指定的 LLM 配置。"""
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
    """删除指定的 LLM 配置。"""
    deleted = await llm_config_service.delete_config(session, config_id)
    if not deleted:
        return APIResponse(code=404, message="Config not found")
    return APIResponse()


@router.post("/llm/test", response_model=APIResponse)
async def test_llm_connection(body: LLMConfigTestRequest) -> APIResponse:
    """测试 LLM 提供商连通性（不保存配置）。"""
    result = await llm_config_service.test_connection(
        body.provider, body.api_key, body.model_name, body.base_url,
    )
    return APIResponse(data=result)


def _serialize(config: LLMConfigModel) -> dict[str, object]:
    """将数据库模型序列化为前端响应格式（API Key 脱敏）。"""
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
