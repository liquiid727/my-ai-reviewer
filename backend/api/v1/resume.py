"""简历相关 API 端点 —— 上传、查询状态、查看详情、重试和获取评估结果。"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import (
    APIResponse,
    CandidateProfileData,
    EvaluationData,
    ResumeDetailData,
    ResumeFactData,
    ResumeStatusData,
    ResumeUploadData,
)
from backend.application.llm_config_service import has_verified_config
from backend.application.plan_queries import get_eligible_resume_options
from backend.application.resume_service import privacy as privacy_uc
from backend.application.resume_service import queries as resume_queries
from backend.application.resume_service import upload_resume
from backend.domain.resume.enums import ResumeStatus
from backend.infrastructure.db.database import get_db

router = APIRouter(prefix="/resume", tags=["resume"])

# LLM 未就绪（无已激活且已验证配置）时的门禁错误码，供前端识别引导配置
LLM_NOT_READY_CODE = 428
LLM_NOT_READY_MESSAGE = "LLM not configured or not verified"


class ManualPrivacySpan(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    entity_type: str


class PrivacyMasksRequest(BaseModel):
    base_revision: int = Field(ge=1)
    spans: list[ManualPrivacySpan] = Field(min_length=1, max_length=50)


class PrivacyApproveRequest(BaseModel):
    base_revision: int = Field(ge=1)


@router.post("/upload", response_model=APIResponse)
async def upload_resume_endpoint(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """上传简历文件，自动触发处理流水线。

    硬门禁：必须存在已激活且已验证的 LLM 配置，否则拒绝上传，
    避免后续解析/评估管道必然失败的无效上传。
    """
    if not await has_verified_config(session):
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)

    file_data = await file.read()
    result = await upload_resume(
        session=session,
        filename=file.filename or "unknown",
        file_data=file_data,
    )
    return APIResponse(data=ResumeUploadData(**result))


@router.get("", response_model=APIResponse)
async def list_resumes(
    has_profile: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """List lightweight resume options for plan creation without exposing profile identity."""
    if not has_profile:
        return APIResponse(code=1001, message="has_profile=true is required for this listing")
    items, total = await get_eligible_resume_options(session, page=page, page_size=page_size)
    return APIResponse(data={"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/{resume_id}/status", response_model=APIResponse)
async def get_resume_status(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """查询简历的处理状态和进度。"""
    payload = await resume_queries.build_status_payload(session, resume_id)
    if payload is None:
        return APIResponse(code=404, message="Resume not found")
    return APIResponse(data=ResumeStatusData(**payload).model_dump())


@router.get("/{resume_id}", response_model=APIResponse)
async def get_resume_detail(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历详情（仅含脱敏文本和 LLM 解析结果）。"""
    payload = await resume_queries.build_detail_payload(session, resume_id)
    if payload is None:
        return APIResponse(code=404, message="Resume not found")
    return APIResponse(data=ResumeDetailData(**payload).model_dump(mode="json"))


@router.get("/{resume_id}/privacy", response_model=APIResponse)
async def get_privacy_review(
    resume_id: uuid.UUID,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    resume, manifest = await privacy_uc.load_privacy_records(session, resume_id)
    if resume is None or manifest is None:
        return APIResponse(code=404, message="Privacy review not found")
    if await privacy_uc.expire_quarantine_if_needed(session, resume, manifest):
        return APIResponse(code=410, message="Privacy review expired")
    return APIResponse(
        data={
            "resume_id": str(resume.id),
            "status": manifest.status,
            "revision": manifest.revision,
            "masked_text": resume.masked_text,
            "placeholders": manifest.placeholders,
            "risk_flags": manifest.risk_flags,
            "quarantine_expires_at": (
                manifest.quarantine_expires_at.isoformat() if manifest.quarantine_expires_at else None
            ),
        }
    )


@router.post("/{resume_id}/privacy/masks", response_model=APIResponse)
async def add_privacy_masks(
    resume_id: uuid.UUID,
    body: PrivacyMasksRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    resume, manifest = await privacy_uc.load_privacy_records(session, resume_id)
    if resume is None or manifest is None:
        return APIResponse(code=404, message="Privacy review not found")
    if await privacy_uc.expire_quarantine_if_needed(session, resume, manifest):
        return APIResponse(code=410, message="Privacy review expired")
    if manifest.status != "review_required":
        return APIResponse(code=1003, message="Privacy review is not editable")
    if manifest.revision != body.base_revision:
        return APIResponse(code=409, message="Privacy review revision conflict")
    try:
        data = await privacy_uc.apply_privacy_masks(
            session,
            resume=resume,
            manifest=manifest,
            spans=[(span.start, span.end, span.entity_type) for span in body.spans],
        )
    except ValueError:
        return APIResponse(code=1001, message="Invalid privacy mask span")
    return APIResponse(data=data)


@router.post("/{resume_id}/privacy/approve", response_model=APIResponse)
async def approve_privacy(
    resume_id: uuid.UUID,
    body: PrivacyApproveRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    resume, manifest = await privacy_uc.load_privacy_records(session, resume_id)
    if resume is None or manifest is None:
        return APIResponse(code=404, message="Privacy review not found")
    if await privacy_uc.expire_quarantine_if_needed(session, resume, manifest):
        return APIResponse(code=410, message="Privacy review expired")
    if manifest.status != "review_required":
        return APIResponse(code=1003, message="Privacy review cannot be approved")
    if manifest.revision != body.base_revision:
        return APIResponse(code=409, message="Privacy review revision conflict")
    try:
        data = await privacy_uc.approve_privacy_review(session, resume=resume, manifest=manifest)
    except ValueError:
        return APIResponse(code=422, message="Residual sensitive data detected")
    return APIResponse(data=data)


@router.get("/{resume_id}/facts", response_model=APIResponse)
async def get_resume_facts(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历抽取出的全部可追溯事实。"""
    facts = await resume_queries.list_fact_payloads(session, resume_id)
    if facts is None:
        return APIResponse(code=404, message="Resume not found")
    data = [ResumeFactData(**f).model_dump(mode="json") for f in facts]
    return APIResponse(data=data)


@router.get("/{resume_id}/profile", response_model=APIResponse)
async def get_candidate_profile(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历对应的候选人画像（独立落库，便于检索与审计）。"""
    payload = await resume_queries.get_profile_payload(session, resume_id)
    if payload is None:
        return APIResponse(code=404, message="Resume not found")
    if payload.get("_missing_profile"):
        return APIResponse(code=404, message="No candidate profile found for this resume")
    data = CandidateProfileData(**payload).model_dump(mode="json")
    return APIResponse(data=data)


@router.post("/{resume_id}/retry", response_model=APIResponse)
async def retry_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """重试失败的简历处理流水线。"""
    # 重跑流水线同样依赖 LLM，与上传保持一致的硬门禁
    if not await has_verified_config(session):
        return APIResponse(code=LLM_NOT_READY_CODE, message=LLM_NOT_READY_MESSAGE)

    resume = await resume_queries.get_resume_for_mutation(session, resume_id)
    if resume is None:
        return APIResponse(code=404, message="Resume not found")

    if resume.status != ResumeStatus.FAILED.value:
        return APIResponse(code=400, message="Resume is not in failed state")
    if resume.file_id is None:
        return APIResponse(code=410, message="Original resume quarantine is no longer available")

    try:
        await privacy_uc.retry_failed_resume(session, resume)
    except Exception:
        return APIResponse(code=503, message="Pipeline dispatch failed, please retry later")

    return APIResponse(
        message="Pipeline restarted",
        data=ResumeStatusData(
            status=ResumeStatus.UPLOADED.value,
            current_step="text_extract",
            completed_steps=[],
        ).model_dump(),
    )


@router.post("/{resume_id}/reparse", response_model=APIResponse)
async def reparse_resume_endpoint(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """对任意已存简历重新解析（从 text_extract 起重跑），并保留上一版本快照。

    与 /retry 不同：/retry 仅适用于 failed 状态；/reparse 适用于任意状态（如
    parser/extractor 版本升级后对历史简历重跑），并将当前结果快照入历史。
    """
    existing = await resume_queries.get_resume_for_mutation(session, resume_id)
    if existing is None:
        return APIResponse(code=404, message="Resume not found")
    if existing.file_id is None:
        return APIResponse(code=410, message="Original resume quarantine is no longer available")
    try:
        await privacy_uc.reparse_resume(session, resume_id)
    except ValueError:
        return APIResponse(code=404, message="Resume not found")
    except Exception:
        return APIResponse(code=503, message="Pipeline dispatch failed, please retry later")

    return APIResponse(
        message="Re-parse started",
        data=ResumeStatusData(
            status=ResumeStatus.UPLOADED.value,
            current_step="text_extract",
            completed_steps=[],
        ).model_dump(),
    )


@router.get("/{resume_id}/evaluation", response_model=APIResponse)
async def get_evaluation(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取简历的 LLM 评估结果（取最新一次评估）。"""
    payload = await resume_queries.get_evaluation_payload(session, resume_id)
    if payload is None:
        return APIResponse(code=404, message="Resume not found")
    if payload.get("_missing_evaluation"):
        return APIResponse(code=404, message="No evaluation found for this resume")
    return APIResponse(data=EvaluationData(**payload).model_dump(mode="json"))
