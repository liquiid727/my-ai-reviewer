from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse, ResumeUploadData
from backend.application.resume_service import upload_resume
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload", response_model=APIResponse)
async def upload_resume_endpoint(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    file_data = await file.read()
    result = await upload_resume(
        session=session,
        filename=file.filename or "unknown",
        file_data=file_data,
    )
    return APIResponse(data=ResumeUploadData(**result))
