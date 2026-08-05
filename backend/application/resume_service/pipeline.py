"""Resume processing pipeline use cases (application layer).

Pipeline: text extract → privacy mask → LLM extract → classify → evaluate.
Owns session/status transitions and infrastructure adapter calls.
"""

import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.llm_config_service import get_active_verified_config
from backend.application.resume_service.diagnostics import (
    RESUME_PROCESSING_FAILED,
    build_failure_details,
    error_code_for_exception,
    public_error_message,
)
from backend.application.resume_service.runs import load_owned_resume
from backend.config import get_settings
from backend.domain.privacy import PrivacyGuard, ResumePrivacyRedactor
from backend.domain.resume.enums import ResumeStatus, resume_status_value
from backend.domain.resume.policies import build_reparse_history_payload
from backend.domain.resume.schemas import CandidateProfile
from backend.infrastructure.classifiers.rule_classifier import RuleBasedResumeClassifier
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    FileModel,
    ResumeEvaluationModel,
    ResumeFactModel,
    ResumeModel,
    ResumePrivacyManifestModel,
    ResumeSectionModel,
)
from backend.infrastructure.evaluators.llm_evaluator import LLMResumeEvaluator
from backend.infrastructure.extractors.llm_extractor import LLMResumeExtractor
from backend.infrastructure.extractors.section_splitter import split_sections
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.privacy import QuarantineCipher
from backend.infrastructure.storage.minio_client import delete_file, download_file


async def _release_db_transaction(session: AsyncSession) -> None:
    """Release a read transaction before external work (test doubles may omit rollback)."""
    rollback = getattr(session, "rollback", None)
    if rollback is not None:
        await rollback()


async def _current_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
    expected_run_id: uuid.UUID | None = None,
) -> ResumeModel | None:
    """Load the resume only when this worker still owns its processing run."""

    if expected_run_id is not None:
        return await load_owned_resume(session, resume_id=resume_id, run_id=expected_run_id)
    return await session.get(ResumeModel, resume_id)


async def _persist_failure(
    session: AsyncSession,
    resume_id: uuid.UUID,
    *,
    expected_run_id: uuid.UUID | None,
    step: str,
    error_code: str = RESUME_PROCESSING_FAILED,
) -> None:
    """Persist only a safe failure summary if this run is still current."""

    resume = await _current_resume(session, resume_id, expected_run_id)
    if resume is None:
        await _release_db_transaction(session)
        return
    resume.status = ResumeStatus.FAILED.value
    resume.parse_error = public_error_message(error_code)
    resume.processing_error_details = build_failure_details(error_code, step=step)
    await session.commit()


@dataclass(frozen=True)
class _ExtractedSource:
    """Thread-bound parser output; no blocking storage/parser work on the loop."""

    parser_version: str
    masked_text: str
    placeholders: list[dict[str, Any]]
    risk_flags: list[Any]
    parsed_result: dict[str, Any]


def _read_and_redact_source(
    *,
    bucket: str,
    storage_path: str,
    extension: str,
    encryption_key: str,
) -> _ExtractedSource:
    """Download, decrypt, parse and redact a quarantined file off the event loop."""
    encrypted = download_file(bucket, storage_path)
    file_bytes = QuarantineCipher(encryption_key).decrypt(encrypted)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(file_bytes)
            temporary_path = tmp.name

        parser = get_parser(extension)
        result = parser.parse(temporary_path)
        redaction = ResumePrivacyRedactor().redact(result.raw_text)
        PrivacyGuard().assert_masked(redaction.masked_text)
        parsed: dict[str, Any] = {
            "text_blocks": [
                {
                    "type": block.type,
                    "text": ResumePrivacyRedactor().redact(block.text).masked_text,
                    "page": block.page,
                }
                for block in result.blocks
            ],
        }
        return _ExtractedSource(
            parser_version=parser.version,
            masked_text=redaction.masked_text,
            placeholders=[placeholder.model_dump(mode="json") for placeholder in redaction.manifest.placeholders],
            risk_flags=redaction.manifest.risk_flags,
            parsed_result=parsed,
        )
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


async def _get_resume_llm_gateway(session: AsyncSession) -> LLMGateway:
    """Build a gateway from the active, verified database configuration."""
    config = await get_active_verified_config(session)
    if config is None:
        raise ValueError("LLM not configured or not verified")
    return LLMGateway.from_config(config)


async def detach_resume_file(
    session: AsyncSession,
    resume: ResumeModel,
    file_record: FileModel | None,
) -> None:
    """Null the resume FK, flush, then delete the file row (FK-safe order)."""
    resume.file_id = None
    await session.flush()
    if file_record is not None:
        await session.delete(file_record)


async def get_privacy_manifest(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumePrivacyManifestModel | None:
    """Load the privacy manifest through its unique resume reference."""
    return cast(
        ResumePrivacyManifestModel | None,
        await session.scalar(
            select(ResumePrivacyManifestModel).where(ResumePrivacyManifestModel.resume_id == resume_id)
        ),
    )


async def extract_text(
    session: AsyncSession,
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> ResumeModel:
    """步骤一：从文件中提取原始文本。

    从 MinIO 下载文件 → 根据扩展名选择解析器 → 提取文本并保存。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    file_record = await session.get(FileModel, resume.file_id)
    if file_record is None:
        raise ValueError(f"File not found for resume: {resume_id}")

    settings = get_settings()
    ext = Path(file_record.original_name).suffix
    try:
        encryption_key = settings.PRIVACY_QUARANTINE_KEY or settings.ENCRYPTION_KEY
        if not encryption_key:
            raise RuntimeError("Privacy quarantine key is not configured")
        storage_path = file_record.storage_path
        # Snapshot the source row, then release the DB transaction while
        # object storage and document parsers perform potentially slow I/O.
        await _release_db_transaction(session)
        extracted = await asyncio.to_thread(
            _read_and_redact_source,
            bucket=settings.MINIO_BUCKET_QUARANTINE,
            storage_path=storage_path,
            extension=ext,
            encryption_key=encryption_key,
        )

        if run_id is None:
            resume = await session.get(ResumeModel, resume_id)
        else:
            resume = await load_owned_resume(session, resume_id=resume_id, run_id=run_id)
            if resume is None:
                await _release_db_transaction(session)
                return ResumeModel(id=resume_id, status="stale")
        if resume is None:
            raise ValueError(f"Resume not found: {resume_id}")

        if not extracted.masked_text.strip():
            resume.status = ResumeStatus.FAILED.value
            resume.parse_error = public_error_message(RESUME_PROCESSING_FAILED)
            resume.processing_error_details = build_failure_details(
                RESUME_PROCESSING_FAILED,
                step="text_extract",
            )
            resume.parser_version = extracted.parser_version
            await session.commit()
            return resume

        resume.masked_text = extracted.masked_text
        resume.parser_version = extracted.parser_version
        resume.parse_error = None
        # 将结构化文本块（Paragraph/Heading/Block/Page）可选落库到 parsed_result
        prior = resume.parsed_result or {}
        parsed = extracted.parsed_result
        # 重解析场景：保留历史版本快照
        if prior.get("history"):
            parsed["history"] = prior["history"]
        resume.parsed_result = parsed
        manifest = await get_privacy_manifest(session, resume_id)
        if manifest is None:
            raise ValueError(f"Privacy manifest not found: {resume_id}")
        manifest.placeholders = extracted.placeholders
        manifest.risk_flags = extracted.risk_flags
        review_required = bool(manifest.risk_flags) or settings.PRIVACY_REVIEW_REQUIRED
        if review_required:
            manifest.status = "review_required"
            resume.status = ResumeStatus.PRIVACY_REVIEW_REQUIRED.value
        else:
            manifest.status = "approved"
            manifest.reviewed_at = datetime.now(timezone.utc)
            quarantine_path = manifest.quarantine_path
            if quarantine_path:
                await asyncio.to_thread(
                    delete_file,
                    settings.MINIO_BUCKET_QUARANTINE,
                    quarantine_path,
                )
            manifest.quarantine_path = None
            manifest.quarantine_expires_at = None
            current_file = await session.get(FileModel, resume.file_id)
            await detach_resume_file(session, resume, current_file)
            resume.status = ResumeStatus.TEXT_MASKED.value
        await session.commit()

    except Exception as exc:
        await _release_db_transaction(session)
        if run_id is None:
            failed_resume = await session.get(ResumeModel, resume_id)
            if failed_resume is not None:
                failed_resume.status = ResumeStatus.FAILED.value
                # Never persist provider/parser exception text: it may contain
                # input excerpts, credentials, or response payloads.
                error_code = error_code_for_exception(exc)
                failed_resume.parse_error = public_error_message(error_code)
                failed_resume.processing_error_details = build_failure_details(
                    error_code,
                    step="text_extract",
                )
                await session.commit()
        raise

    return resume


async def extract_facts(
    session: AsyncSession,
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> ResumeModel:
    """步骤二：调用 LLM 对原始文本进行结构化信息提取。

    将文本发送给大模型，提取候选人画像、事实列表等结构化数据。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    if not resume.masked_text:
        raise ValueError(f"No masked text for resume: {resume_id}")
    manifest = await get_privacy_manifest(session, resume_id)
    if manifest is None or manifest.status != "approved":
        raise ValueError(f"Resume privacy is not approved: {resume_id}")
    PrivacyGuard().assert_masked(resume.masked_text)

    masked_text = resume.masked_text
    gateway = await _get_resume_llm_gateway(session)
    extractor = LLMResumeExtractor(gateway)
    # The provider call must not retain a database transaction or row lock.
    await _release_db_transaction(session)
    result = await extractor.extract(masked_text)

    if run_id is None:
        resume = await session.get(ResumeModel, resume_id)
    else:
        resume = await load_owned_resume(session, resume_id=resume_id, run_id=run_id)
        if resume is None:
            await _release_db_transaction(session)
            return ResumeModel(id=resume_id, status="stale")
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    # 保留文本提取阶段落库的结构化文本块与历史快照，避免被 LLM 解析结果覆盖
    prior = resume.parsed_result or {}
    if "text_blocks" in prior:
        result["text_blocks"] = prior["text_blocks"]
    if "history" in prior:
        result["history"] = prior["history"]

    resume.parsed_result = result

    # 落库：将结构化事实、语义区块与候选人画像持久化，实现「可追溯」
    facts = result.get("facts")
    profile = result.get("profile")
    if facts:
        await _persist_facts(session, resume_id, facts, extractor.version)
    if profile:
        await _persist_sections(session, resume_id, profile, result.get("text_blocks"))
        await _upsert_candidate_profile(session, resume_id, profile, extractor.version)

    resume.status = ResumeStatus.FACT_EXTRACTED.value
    await session.commit()

    return resume


async def classify_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> ResumeModel:
    """步骤三：基于规则对候选人画像进行分类。

    根据技能关键词、工作年限等维度，生成技术方向标签、资历等级和行业标签。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    parsed_result: dict[str, Any] = resume.parsed_result or {}
    profile_data = parsed_result.get("profile")
    if profile_data is None:
        raise ValueError(f"No parsed profile for resume: {resume_id}")

    profile = CandidateProfile.model_validate(profile_data)

    classifier = RuleBasedResumeClassifier()
    await _release_db_transaction(session)
    result = await asyncio.to_thread(classifier.classify, profile)

    if run_id is None:
        resume = await session.get(ResumeModel, resume_id)
    else:
        resume = await load_owned_resume(session, resume_id=resume_id, run_id=run_id)
        if resume is None:
            await _release_db_transaction(session)
            return ResumeModel(id=resume_id, status="stale")
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    # 将分类结果写回候选人画像的能力标签
    profile.ability_tags = [
        *result.tech_direction_tags,
        result.experience_level,
        *result.industry_tags,
    ]

    # 更新解析结果中的画像和分类数据
    parsed_result["profile"] = profile.model_dump(mode="json")
    parsed_result["classification"] = {
        "tech_direction_tags": result.tech_direction_tags,
        "experience_level": result.experience_level,
        "industry_tags": result.industry_tags,
        "stats": result.stats,
        "classifier_version": classifier.version,
    }

    # 分类后画像的 ability_tags 已更新，重新落库以保持可追溯
    await _upsert_candidate_profile(session, resume_id, parsed_result["profile"], classifier.version)

    resume.parsed_result = parsed_result
    resume.status = ResumeStatus.CLASSIFIED.value
    await session.commit()

    return resume


async def evaluate_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> ResumeModel:
    """步骤四：调用 LLM 对简历进行多维度评估打分。

    从 8 个维度（技术能力、项目质量、工程能力等）评估候选人，
    生成综合评分、优劣势分析和面试建议。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    parsed_result: dict[str, Any] = resume.parsed_result or {}
    if not parsed_result:
        raise ValueError(f"No parsed result for resume: {resume_id}")
    PrivacyGuard().assert_masked(parsed_result)

    gateway = await _get_resume_llm_gateway(session)
    evaluator = LLMResumeEvaluator(gateway)
    # The provider call must not retain a database transaction or row lock.
    await _release_db_transaction(session)
    evaluation = await evaluator.evaluate(parsed_result)

    if run_id is None:
        resume = await session.get(ResumeModel, resume_id)
    else:
        resume = await load_owned_resume(session, resume_id=resume_id, run_id=run_id)
        if resume is None:
            await _release_db_transaction(session)
            return ResumeModel(id=resume_id, status="stale")
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    # 提取元信息（模型名称、token 用量等）后保存评估记录
    meta = evaluation.pop("_meta", {})

    eval_record = ResumeEvaluationModel(
        resume_id=resume_id,
        overall_score=evaluation["overall_score"],
        dimension_scores=evaluation.get("dimension_scores", []),
        strengths=evaluation.get("strengths", []),
        risks=evaluation.get("risks", []),
        interview_suggestions=evaluation.get("interview_suggestions", {}),
        summary=evaluation.get("summary"),
        llm_model=meta.get("model"),
    )
    session.add(eval_record)

    resume.status = ResumeStatus.EVALUATED.value
    await session.commit()

    return resume


async def snapshot_and_reset_for_reparse(
    session: AsyncSession,
    resume_id: uuid.UUID,
    *,
    commit: bool = True,
) -> ResumeModel:
    """为重解析保存当前版本快照并重置状态到 uploaded（幂等追加历史）。

    将当前 parsed_result（含 profile/facts/classification/text_blocks）连同
    parser_version 一起快照入 parsed_result["history"]，随后重置状态以便
    从 text_extract 重跑整条流水线。流水线的 facts/sections/profile 均为
    按 resume_id 覆盖式写入，evaluation 为追加式，因此不破坏已有
    evaluation / interview 关联。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    resume.parsed_result = build_reparse_history_payload(
        prior_parsed_result=resume.parsed_result or {},
        parser_version=resume.parser_version,
        status=resume_status_value(resume.status),
        snapshot_at_iso=datetime.now(timezone.utc).isoformat(),
    )
    resume.status = ResumeStatus.UPLOADED.value
    resume.parse_error = None
    if commit:
        await session.commit()

    return resume


async def _persist_sections(
    session: AsyncSession,
    resume_id: uuid.UUID,
    profile: dict[str, Any],
    text_blocks: list[dict[str, Any]] | None = None,
) -> None:
    """生成可追溯的语义区块记录（幂等）。

    优先使用解析阶段落库的结构化文本块做独立的标题启发式切分
    （覆盖 basic_info/awards/self_evaluation 等 LLM 画像不含的区块）；
    切分不出结果时回退到基于画像顶层区块的方式。
    """
    PrivacyGuard().assert_masked({"profile": profile, "text_blocks": text_blocks or []})
    await session.execute(delete(ResumeSectionModel).where(ResumeSectionModel.resume_id == resume_id))

    sections = split_sections(text_blocks) if text_blocks else []
    if sections:
        for index, section in enumerate(sections):
            session.add(
                ResumeSectionModel(
                    resume_id=resume_id,
                    section_index=index,
                    section_type=section.section_type.value,
                    title=section.title,
                    raw_text=section.raw_text,
                )
            )
        return

    # 回退：基于 LLM 画像的顶层区块
    import json

    blocks = [
        ("education", profile.get("education")),
        ("work_experience", profile.get("work_experiences")),
        ("project_experience", profile.get("projects")),
        ("skills", profile.get("skills")),
        ("certificates", profile.get("certificates")),
    ]
    index = 0
    for section_type, content in blocks:
        if not content:
            continue
        session.add(
            ResumeSectionModel(
                resume_id=resume_id,
                section_index=index,
                section_type=section_type,
                title=section_type,
                raw_text=json.dumps(content, ensure_ascii=False),
            )
        )
        index += 1


async def _persist_facts(
    session: AsyncSession,
    resume_id: uuid.UUID,
    facts: list[dict[str, Any]],
    extractor_version: str,
) -> None:
    """清空并重新写入该简历的全部事实，保证可追溯且幂等（重试不重复积累）。"""
    await session.execute(delete(ResumeFactModel).where(ResumeFactModel.resume_id == resume_id))
    for fact in facts:
        evidence = fact.get("evidence") or {}
        session.add(
            ResumeFactModel(
                resume_id=resume_id,
                fact_type=fact.get("fact_type", "unknown"),
                fact_key=str(fact.get("key", "")),
                fact_value=fact.get("value", {}),
                evidence_source_text=evidence.get("source_text"),
                evidence_page=evidence.get("page"),
                evidence_section=evidence.get("section"),
                confidence=float(evidence.get("confidence", 0.0) or 0.0),
                meta=fact.get("metadata", {}),
                parser_version=extractor_version,
            )
        )


async def _upsert_candidate_profile(
    session: AsyncSession,
    resume_id: uuid.UUID,
    profile: dict[str, Any],
    extractor_version: str,
) -> None:
    """按 resume_id 幂等写入候选人画像（删除旧记录后插入新记录）。"""
    await session.execute(delete(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id))
    session.add(
        CandidateProfileModel(
            resume_id=resume_id,
            identity=profile.get("identity", {}),
            education=profile.get("education", []),
            work_experiences=profile.get("work_experiences", []),
            projects=profile.get("projects", []),
            skills=profile.get("skills", []),
            certificates=profile.get("certificates", []),
            ability_tags=profile.get("ability_tags", []),
            interview_clues=profile.get("interview_clues", []),
            risks=profile.get("risks", []),
            parser_version=extractor_version,
        )
    )
