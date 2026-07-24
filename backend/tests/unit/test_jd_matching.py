"""JD 匹配单元测试 —— 覆盖纯函数 _compute_match 的多种场景。"""

from backend.domain.jd.matching import _compute_match
from backend.domain.jd.schemas import RequiredSkill


def _profile(skills, tags=None):
    return {
        "skills": [
            {"name": n, "category": "x", "evidence": f"used {n}", "confidence": 0.9}
            for n in skills
        ],
        "ability_tags": tags or [],
    }


def test_perfect_match_all_critical():
    profile = _profile(["Python", "FastAPI", "PostgreSQL"])
    required = [
        RequiredSkill(name="Python", critical=True),
        RequiredSkill(name="FastAPI", critical=True),
        RequiredSkill(name="PostgreSQL", critical=True),
    ]
    result = _compute_match(profile, required)
    assert result.match_score == 100.0
    assert result.missing_skills == []
    assert result.recommendation == "strong_hire"


def test_missing_critical_skill_downgrades_recommendation():
    profile = _profile(["Python", "FastAPI"])
    required = [
        RequiredSkill(name="Python", critical=True),
        RequiredSkill(name="FastAPI", critical=False),
        RequiredSkill(name="React", critical=True),
    ]
    result = _compute_match(profile, required)
    assert "React" in result.missing_skills
    assert any(r.level == "high" for r in result.risk)
    # 存在关键技能缺口，最高仅「待定」
    assert result.recommendation == "conditional"


def test_alias_normalization_matches():
    profile = _profile(["JavaScript", "TypeScript"])
    required = [RequiredSkill(name="JS", critical=False)]
    result = _compute_match(profile, required)
    assert result.skill_match[0].matched is True


def test_partial_match_score_range():
    profile = _profile(["Python"])
    required = [
        RequiredSkill(name="Python", critical=False),
        RequiredSkill(name="Go", critical=False),
        RequiredSkill(name="Rust", critical=False),
    ]
    result = _compute_match(profile, required)
    # 1/3 命中，非关键，score = 0.3 * (1/3) * 100 ≈ 33.3，应为 conditional/reject
    assert 30.0 <= result.match_score <= 40.0
    assert "Go" in result.missing_skills
    assert result.recommendation in ("conditional", "reject")


def test_ability_tags_count_as_skills():
    profile = _profile([], tags=["kubernetes", "docker"])
    required = [RequiredSkill(name="Kubernetes", critical=False)]
    result = _compute_match(profile, required)
    assert result.skill_match[0].matched is True
