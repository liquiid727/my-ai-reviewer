"""简历领域服务 —— 实现简历处理流水线的四个核心步骤。

流水线顺序：文本提取 → LLM 结构化提取 → 规则分类 → LLM 评估
"""

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.privacy import PrivacyGuard, ResumePrivacyRedactor
from backend.domain.resume.enums import ResumeStatus
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


async def extract_text(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel:
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

    tmp_path: str | None = None
    try:
        # 从对象存储下载文件到本地临时目录
        encrypted = download_file(settings.MINIO_BUCKET_QUARANTINE, file_record.storage_path)
        encryption_key = settings.PRIVACY_QUARANTINE_KEY or settings.ENCRYPTION_KEY
        if not encryption_key:
            raise RuntimeError("Privacy quarantine key is not configured")
        file_bytes = QuarantineCipher(encryption_key).decrypt(encrypted)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # 根据文件类型选择合适的解析器（PDF / DOCX / TXT）
        parser = get_parser(ext)
        result = parser.parse(tmp_path)

        if not result.raw_text.strip():
            resume.status = ResumeStatus.FAILED
            resume.parse_error = "Parsed document contains no text"
            resume.parser_version = parser.version
            await session.commit()
            return resume

        redaction = ResumePrivacyRedactor().redact(result.raw_text)
        PrivacyGuard().assert_masked(redaction.masked_text)
        resume.masked_text = redaction.masked_text
        resume.parser_version = parser.version
        resume.parse_error = None
        # 将结构化文本块（Paragraph/Heading/Block/Page）可选落库到 parsed_result
        prior = resume.parsed_result or {}
        parsed: dict[str, Any] = {
            "text_blocks": [
                {
                    "type": b.type,
                    "text": ResumePrivacyRedactor().redact(b.text).masked_text,
                    "page": b.page,
                }
                for b in result.blocks
            ],
        }
        # 重解析场景：保留历史版本快照
        if prior.get("history"):
            parsed["history"] = prior["history"]
        resume.parsed_result = parsed
        manifest = await session.get(ResumePrivacyManifestModel, resume_id)
        if manifest is None:
            raise ValueError(f"Privacy manifest not found: {resume_id}")
        manifest.placeholders = [p.model_dump(mode="json") for p in redaction.manifest.placeholders]
        manifest.risk_flags = redaction.manifest.risk_flags
        review_required = bool(manifest.risk_flags) or settings.PRIVACY_REVIEW_REQUIRED
        if review_required:
            manifest.status = "review_required"
            resume.status = ResumeStatus.PRIVACY_REVIEW_REQUIRED
        else:
            manifest.status = "approved"
            manifest.reviewed_at = datetime.now(timezone.utc)
            quarantine_path = manifest.quarantine_path
            if quarantine_path:
                delete_file(settings.MINIO_BUCKET_QUARANTINE, quarantine_path)
            manifest.quarantine_path = None
            manifest.quarantine_expires_at = None
            resume.file_id = None
            await session.delete(file_record)
            resume.status = ResumeStatus.TEXT_MASKED
        await session.commit()

    except Exception as exc:
        resume.status = ResumeStatus.FAILED
        resume.parse_error = str(exc)
        await session.commit()
        raise

    finally:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return resume


async def extract_facts(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel:
    """步骤二：调用 LLM 对原始文本进行结构化信息提取。

    将文本发送给大模型，提取候选人画像、事实列表等结构化数据。
    """
    resume = await session.get(ResumeModel, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")

    if not resume.masked_text:
        raise ValueError(f"No masked text for resume: {resume_id}")
    manifest = await session.get(ResumePrivacyManifestModel, resume_id)
    if manifest is None or manifest.status != "approved":
        raise ValueError(f"Resume privacy is not approved: {resume_id}")
    PrivacyGuard().assert_masked(resume.masked_text)

    gateway = LLMGateway.from_settings()
    extractor = LLMResumeExtractor(gateway)
    result = await extractor.extract(resume.masked_text)

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

    resume.status = ResumeStatus.FACT_EXTRACTED
    await session.commit()

    return resume


async def classify_resume(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel:
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
    result = classifier.classify(profile)

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
    resume.status = ResumeStatus.CLASSIFIED
    await session.commit()

    return resume


async def evaluate_resume(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel:
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

    gateway = LLMGateway.from_settings()
    evaluator = LLMResumeEvaluator(gateway)
    evaluation = await evaluator.evaluate(parsed_result)

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

    resume.status = ResumeStatus.EVALUATED
    await session.commit()

    return resume


async def snapshot_and_reset_for_reparse(
    session: AsyncSession,
    resume_id: uuid.UUID,
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

    prior = resume.parsed_result or {}
    history = list(prior.get("history", []))
    # 快照不含 history 自身，避免历史递归膨胀
    snapshot_payload = {k: v for k, v in prior.items() if k != "history"}
    if snapshot_payload or resume.parser_version:
        history.append({
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": resume.parser_version,
            "status": str(resume.status),
            "parsed_result": snapshot_payload,
        })

    resume.parsed_result = {"history": history}
    resume.status = ResumeStatus.UPLOADED
    resume.parse_error = None
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
            session.add(ResumeSectionModel(
                resume_id=resume_id,
                section_index=index,
                section_type=section.section_type.value,
                title=section.title,
                raw_text=section.raw_text,
            ))
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
        session.add(ResumeSectionModel(
            resume_id=resume_id,
            section_index=index,
            section_type=section_type,
            title=section_type,
            raw_text=json.dumps(content, ensure_ascii=False),
        ))
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
        session.add(ResumeFactModel(
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
        ))


async def _upsert_candidate_profile(
    session: AsyncSession,
    resume_id: uuid.UUID,
    profile: dict[str, Any],
    extractor_version: str,
) -> None:
    """按 resume_id 幂等写入候选人画像（删除旧记录后插入新记录）。"""
    await session.execute(
        delete(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id)
    )
    session.add(CandidateProfileModel(
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
    ))
