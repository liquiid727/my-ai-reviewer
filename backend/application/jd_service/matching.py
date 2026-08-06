"""JD matching use cases: load profile, score, persist match row."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.domain.jd.policies import compute_match
from backend.domain.jd.schemas import RequiredSkill
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JDMatchResultModel,
    JobDescriptionModel,
)


class JDMatchingService:
    """JD matching service: load candidate profile, compute match, persist result."""

    async def match(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
        jd: JobDescriptionModel,
    ) -> JDMatchResultModel:
        """Match resume to JD and write a jd_match_results row."""
        stmt = (
            select(CandidateProfileModel)
            .where(CandidateProfileModel.resume_id == resume_id)
            .options(noload(CandidateProfileModel.resume))
        )
        result = await session.execute(stmt)
        profile_row = result.scalar_one_or_none()
        if profile_row is None:
            raise ValueError(f"No candidate profile found for resume: {resume_id}")

        profile_dict = {
            "skills": profile_row.skills or [],
            "ability_tags": profile_row.ability_tags or [],
            "identity": profile_row.identity or {},
        }

        required = [
            RequiredSkill(name=s.get("name", ""), critical=bool(s.get("critical", False)))
            for s in (jd.required_skills or [])
            if s.get("name")
        ]
        # Compat: string-list required_skills
        if not required and isinstance(jd.required_skills, list):
            required = [RequiredSkill(name=str(s)) for s in jd.required_skills if isinstance(s, (str, int))]

        match = compute_match(profile_dict, required)

        record = JDMatchResultModel(
            resume_id=resume_id,
            jd_id=jd.id,
            match_score=match.match_score,
            mode="rules_v1",
            status="ready",
            matcher_version="rules-v1",
            skill_match=[m.model_dump() for m in match.skill_match],
            missing_skills=match.missing_skills,
            risk=[r.model_dump() for r in match.risk],
            gap=[g.model_dump() for g in match.gap],
            recommendation=match.recommendation,
            detail=match.detail,
        )
        session.add(record)
        await session.flush()
        return record


async def match_resume_to_jd(
    session: AsyncSession,
    resume_id: uuid.UUID,
    jd: JobDescriptionModel,
) -> JDMatchResultModel:
    return await JDMatchingService().match(session, resume_id, jd)


__all__ = ["JDMatchingService", "match_resume_to_jd"]
