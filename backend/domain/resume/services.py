"""简历领域服务 —— 实现简历处理流水线的四个核心步骤。

流水线顺序：文本提取 → LLM 结构化提取 → 规则分类 → LLM 评估
"""

import os
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.domain.resume.enums import ResumeStatus
from backend.domain.resume.schemas import CandidateProfile
from backend.infrastructure.classifiers.rule_classifier import RuleBasedResumeClassifier
from backend.infrastructure.db.models import FileModel, ResumeEvaluationModel, ResumeModel
from backend.infrastructure.evaluators.llm_evaluator import LLMResumeEvaluator
from backend.infrastructure.extractors.llm_extractor import LLMResumeExtractor
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.storage.minio_client import download_file


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
        file_bytes = download_file(settings.MINIO_BUCKET_RESUMES, file_record.storage_path)

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

        resume.raw_text = result.raw_text
        resume.parser_version = parser.version
        resume.parse_error = None
        resume.status = ResumeStatus.TEXT_PARSED
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

    if not resume.raw_text:
        raise ValueError(f"No raw text for resume: {resume_id}")

    gateway = LLMGateway.from_settings()
    extractor = LLMResumeExtractor(gateway)
    result = await extractor.extract(resume.raw_text)

    resume.parsed_result = result
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

    parsed_result: dict = resume.parsed_result or {}
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

    parsed_result: dict = resume.parsed_result or {}
    if not parsed_result:
        raise ValueError(f"No parsed result for resume: {resume_id}")

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
