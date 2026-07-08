from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class ResumeUploadData(BaseModel):
    resume_id: str
    file_id: str
    status: str
