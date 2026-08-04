"""POST /jd 自动抽取集成单测 —— 自动抽取 / 手动跳过 / 502 失败 / 空输入（免数据库）。

直接调用端点函数，monkeypatch 掉 _get_extractor，_FakeSession 充当 AsyncSession。
"""

import uuid
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1 import jd as api
from backend.domain.jd.schemas import (
    ExtractedSkill,
    JDExtraction,
    JobDescriptionInput,
)
from backend.infrastructure.extractors.jd_extractor import JDExtractionError

JD_ID = uuid.UUID("00000000-0000-0000-0000-000000000037")


class _FakeSession:
    """充当 AsyncSession：记录 add/commit，flush 时补 id/created_at。"""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            obj.id = JD_ID
            obj.created_at = datetime.now(timezone.utc)

    async def commit(self) -> None:
        self.committed = True


class _FakeExtractor:
    """打桩抽取器：返回预置结果或抛出预置异常，记录调用次数。"""

    def __init__(
        self,
        result: JDExtraction | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    async def extract(self, raw_text: str) -> JDExtraction:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _extraction() -> JDExtraction:
    return JDExtraction(
        required_skills=[
            ExtractedSkill(name="Python", critical=True, evidence="精通 Python"),
            ExtractedSkill(name="FastAPI", critical=False, evidence=None),
        ],
        responsibilities=["负责后端服务开发", "参与架构设计"],
        seniority="senior",
    )


class TestCreateJobDescription:
    """POST /jd。"""

    async def test_auto_extraction_when_no_skills(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """未传 required_skills 且 raw_text 非空：走 LLM 抽取，extraction_source=llm。"""
        extractor = _FakeExtractor(result=_extraction())
        monkeypatch.setattr(api, "_get_extractor", lambda: extractor)
        session = _FakeSession()

        resp = await api.create_job_description(
            JobDescriptionInput(title="后端工程师", raw_text="精通 Python，熟悉 FastAPI"),
            cast(AsyncSession, session),
        )

        assert resp.code == 0
        assert extractor.calls == 1
        data = resp.data
        assert data["extraction_source"] == "llm"
        assert data["required_skills"] == [
            {"name": "Python", "critical": True, "evidence": "精通 Python"},
            {"name": "FastAPI", "critical": False, "evidence": None},
        ]
        assert data["responsibilities"] == ["负责后端服务开发", "参与架构设计"]
        assert data["seniority"] == "senior"
        assert session.committed is True

    async def test_manual_skills_skip_extraction(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """显式传入 required_skills：跳过抽取器，extraction_source=manual（回归）。"""
        extractor = _FakeExtractor(error=AssertionError("should not be called"))
        monkeypatch.setattr(api, "_get_extractor", lambda: extractor)
        session = _FakeSession()

        resp = await api.create_job_description(
            JobDescriptionInput(
                raw_text="JD 原文",
                required_skills=["Python", "Go"],
                critical_skills=["Python"],
            ),
            cast(AsyncSession, session),
        )

        assert resp.code == 0
        assert extractor.calls == 0
        data = resp.data
        assert data["extraction_source"] == "manual"
        assert data["required_skills"] == [
            {"name": "Python", "critical": True},
            {"name": "Go", "critical": False},
        ]
        assert session.committed is True

    async def test_extraction_failure_returns_502_without_persisting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """抽取失败：502 JD_EXTRACTION_FAILED，且不落库。"""
        extractor = _FakeExtractor(error=JDExtractionError("llm exhausted"))
        monkeypatch.setattr(api, "_get_extractor", lambda: extractor)
        session = _FakeSession()

        with pytest.raises(HTTPException) as exc_info:
            await api.create_job_description(
                JobDescriptionInput(raw_text="精通 Python"),
                cast(AsyncSession, session),
            )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "JD_EXTRACTION_FAILED"
        assert session.added == []
        assert session.committed is False

    async def test_empty_raw_text_without_skills_keeps_manual(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无技能清单且 raw_text 为空白：不调抽取器，保持空技能 manual 行为。"""
        extractor = _FakeExtractor(error=AssertionError("should not be called"))
        monkeypatch.setattr(api, "_get_extractor", lambda: extractor)
        session = _FakeSession()

        resp = await api.create_job_description(
            JobDescriptionInput(raw_text="   "),
            cast(AsyncSession, session),
        )

        assert resp.code == 0
        assert extractor.calls == 0
        data = resp.data
        assert data["extraction_source"] == "manual"
        assert data["required_skills"] == []
        assert session.committed is True

    async def test_explicit_empty_skills_skip_extraction(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """显式传入 required_skills=[]：视为手动模式，不触发抽取（存量调用方回归）。"""
        extractor = _FakeExtractor(error=AssertionError("should not be called"))
        monkeypatch.setattr(api, "_get_extractor", lambda: extractor)
        session = _FakeSession()

        resp = await api.create_job_description(
            JobDescriptionInput(raw_text="精通 Python", required_skills=[]),
            cast(AsyncSession, session),
        )

        assert resp.code == 0
        assert extractor.calls == 0
        data = resp.data
        assert data["extraction_source"] == "manual"
        assert data["required_skills"] == []
        assert session.committed is True
