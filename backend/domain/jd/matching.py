"""JD 匹配服务 —— 基于规则将候选人画像与岗位要求做确定性匹配。

设计取舍：
- 采用「规则匹配」而非 LLM，保证结果可复现、可测试、零额外调用成本；
- 匹配逻辑聚焦技能重叠度，并区分关键技能与非关键技能，给出匹配分、
  缺失技能、风险、差距与录用建议，覆盖 PRD §8 的全部输出字段。
- 如需更深语义匹配，可在 JDMatchingService.match 前接入 LLM 预解析 JD，
  本模块保留对输入结构的兼容性（required_skills 已是结构化清单）。
"""

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.domain.jd.schemas import (
    GapItem,
    JDMatchResult,
    RequiredSkill,
    RiskItem,
    SkillMatchItem,
)
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JDMatchResultModel,
    JobDescriptionModel,
)

# 常见技能别名归一化，缓解「React / React.js」「JS / JavaScript」等写法差异
_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "nodejs",
    "nodejs": "nodejs",
    "py": "python",
    "golang": "go",
    "c#": "csharp",
    "c++": "cpp",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "tf": "terraform",
    "ml": "machinelearning",
    "ai": "artificialintelligence",
}


def _norm(text: str) -> str:
    """归一化技能名：转小写、去标点，再应用别名映射。"""
    base = re.sub(r"[^a-z0-9+#.]", "", str(text).lower())
    return _ALIASES.get(base, base)


def _match_one(
    req_norm: str,
    candidate_norm: set[str],
    candidate_map: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    """判断单个岗位技能是否被候选人满足，并返回证据。"""
    # 1) 精确（含别名）匹配
    if req_norm in candidate_norm:
        return True, _evidence_for(req_norm, candidate_map)
    # 2) 较长词子的子串匹配（仅当较短词长度 >= 4，避免 go→google 之类误判）
    for c_norm in candidate_norm:
        if len(req_norm) >= 4 and (req_norm in c_norm or c_norm in req_norm):
            return True, _evidence_for(c_norm, candidate_map)
    return False, None


def _evidence_for(norm_key: str, candidate_map: dict[str, dict[str, Any]]) -> str | None:
    """从候选人技能条目中取证据文本。"""
    entry = candidate_map.get(norm_key)
    if not entry:
        return None
    evidence = entry.get("evidence")
    if isinstance(evidence, str) and evidence.strip():
        return evidence.strip()
    name = entry.get("name")
    return name if name else None


def _compute_match(
    profile: dict[str, Any],
    required_skills: list[RequiredSkill],
) -> JDMatchResult:
    """纯函数：根据候选人画像与必备技能清单计算匹配结论。"""
    raw_skills: list[dict[str, Any]] = profile.get("skills") or []
    ability_tags: list[str] = profile.get("ability_tags") or []

    candidate_map: dict[str, dict[str, Any]] = {
        _norm(s.get("name", "")): s for s in raw_skills if s.get("name")
    }
    candidate_norm: set[str] = set(candidate_map) | {_norm(t) for t in ability_tags}

    skill_match: list[SkillMatchItem] = []
    for req in required_skills:
        req_norm = _norm(req.name)
        matched, evidence = _match_one(req_norm, candidate_norm, candidate_map)
        skill_match.append(SkillMatchItem(
            skill=req.name,
            matched=matched,
            critical=req.critical,
            candidate_evidence=evidence,
        ))

    missing_skills = [item.skill for item in skill_match if not item.matched]

    critical_required = [m for m in skill_match if m.critical]
    critical_matched = [m for m in critical_required if m.matched]
    noncritical = [m for m in skill_match if not m.critical]
    noncritical_matched = [m for m in noncritical if m.matched]

    if not skill_match:
        match_score = 0.0
    else:
        critical_ratio = len(critical_matched) / len(critical_required) if critical_required else 1.0
        noncritical_ratio = len(noncritical_matched) / len(noncritical) if noncritical else 1.0
        # 权重仅在「实际存在的关键/非关键技能」间分配，避免缺失类别虚高分数
        if critical_required and noncritical:
            match_score = round(100 * (0.7 * critical_ratio + 0.3 * noncritical_ratio), 1)
        elif critical_required:
            match_score = round(100 * critical_ratio, 1)
        elif noncritical:
            match_score = round(100 * noncritical_ratio, 1)
        else:
            match_score = 0.0

    risk: list[RiskItem] = []
    for item in skill_match:
        if not item.matched and item.critical:
            risk.append(RiskItem(level="high", message=f"缺少关键技能：{item.skill}"))
        elif not item.matched:
            risk.append(RiskItem(level="medium", message=f"缺少加分技能：{item.skill}"))

    gap: list[GapItem] = []
    if missing_skills:
        gap.append(GapItem(
            area="技能",
            description=f"缺失 {len(missing_skills)} 项技能：{', '.join(missing_skills)}",
        ))

    missing_critical = [m for m in skill_match if m.critical and not m.matched]
    if match_score >= 80 and not missing_critical:
        recommendation = "strong_hire"
    elif match_score >= 60 and len(missing_critical) <= 1:
        recommendation = "hire"
    elif match_score >= 40:
        recommendation = "conditional"
    else:
        recommendation = "reject"
    # 存在关键技能缺口时，最高仅给到「待定」
    if any(r.level == "high" for r in risk) and recommendation in ("strong_hire", "hire"):
        recommendation = "conditional"

    detail_parts = [
        f"综合匹配分 {match_score}/100。",
        f"必备技能 {len(skill_match)} 项，命中 {sum(1 for m in skill_match if m.matched)} 项。",
    ]
    if missing_skills:
        detail_parts.append(f"缺失：{', '.join(missing_skills)}。")
    detail_parts.append(f"建议：{recommendation}。")
    detail = " ".join(detail_parts)

    return JDMatchResult(
        match_score=match_score,
        skill_match=skill_match,
        missing_skills=missing_skills,
        risk=risk,
        gap=gap,
        recommendation=recommendation,
        detail=detail,
    )


class JDMatchingService:
    """JD 匹配服务：加载候选人画像、计算匹配并落库结果。"""

    async def match(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
        jd: JobDescriptionModel,
    ) -> JDMatchResultModel:
        """对指定简历与 JD 执行匹配，结果写入 jd_match_results 表。"""
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
        # 兼容仅传字符串列表的场景
        if not required and isinstance(jd.required_skills, list):
            required = [
                RequiredSkill(name=str(s)) for s in jd.required_skills if isinstance(s, (str, int))
            ]

        match = _compute_match(profile_dict, required)

        record = JDMatchResultModel(
            resume_id=resume_id,
            jd_id=jd.id,
            match_score=match.match_score,
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
