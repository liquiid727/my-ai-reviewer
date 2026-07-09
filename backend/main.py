"""FastAPI 应用入口 —— 创建应用实例、注册中间件和路由、定义全局异常处理。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.router import api_router
from backend.config import get_settings
from backend.domain.resume.exceptions import (
    DuplicateResumeError,
    FileTooLargeError,
    UnsupportedFileFormatError,
)

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

# 跨域中间件：允许前端开发服务器的请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API v1 路由
app.include_router(api_router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """健康检查端点，用于探活和就绪探针。"""
    return {"status": "ok"}


# ── 全局异常处理器 ──────────────────────────────────────────

@app.exception_handler(UnsupportedFileFormatError)
async def handle_unsupported_format(request, exc: UnsupportedFileFormatError) -> JSONResponse:  # type: ignore[no-untyped-def]
    """文件格式不支持（如 .exe）时返回 400。"""
    return JSONResponse(status_code=400, content={"code": 1001, "message": "Unsupported file format"})


@app.exception_handler(FileTooLargeError)
async def handle_file_too_large(request, exc: FileTooLargeError) -> JSONResponse:  # type: ignore[no-untyped-def]
    """文件超过大小限制时返回 400。"""
    return JSONResponse(status_code=400, content={"code": 1001, "message": "File too large"})


@app.exception_handler(DuplicateResumeError)
async def handle_duplicate_resume(request, exc: DuplicateResumeError) -> JSONResponse:  # type: ignore[no-untyped-def]
    """简历文件重复上传时直接返回已有的 resume_id，避免重复处理。"""
    return JSONResponse(status_code=200, content={"code": 0, "message": "success", "data": {"resume_id": exc.resume_id}})
