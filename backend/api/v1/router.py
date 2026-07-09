"""API v1 路由汇总 —— 将各子模块的路由注册到统一前缀 /api/v1 下。"""

from fastapi import APIRouter

from backend.api.v1.resume import router as resume_router
from backend.api.v1.settings import router as settings_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(resume_router)   # 简历相关接口
api_router.include_router(settings_router)  # LLM 配置相关接口
