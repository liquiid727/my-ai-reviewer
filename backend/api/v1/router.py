from fastapi import APIRouter

from backend.api.v1.resume import router as resume_router
from backend.api.v1.settings import router as settings_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(resume_router)
api_router.include_router(settings_router)
