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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(UnsupportedFileFormatError)
async def handle_unsupported_format(request, exc: UnsupportedFileFormatError) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=400, content={"code": 1001, "message": "Unsupported file format"})


@app.exception_handler(FileTooLargeError)
async def handle_file_too_large(request, exc: FileTooLargeError) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=400, content={"code": 1001, "message": "File too large"})


@app.exception_handler(DuplicateResumeError)
async def handle_duplicate_resume(request, exc: DuplicateResumeError) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=200, content={"code": 0, "message": "success", "data": {"resume_id": exc.resume_id}})
