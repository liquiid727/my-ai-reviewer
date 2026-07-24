"""重解析（re-parse）单元测试 —— 覆盖版本快照追加、状态重置与幂等。"""

import uuid
from typing import Any

import pytest

from backend.domain.resume.enums import ResumeStatus
from backend.domain.resume.services import snapshot_and_reset_for_reparse


class _FakeResume:
    """最小化的 resume 桩：仅承载快照逻辑访问的字段。"""

    def __init__(self, parsed_result: dict[str, Any] | None, parser_version: str | None, status: str) -> None:
        self.parsed_result = parsed_result
        self.parser_version = parser_version
        self.status = status
        self.parse_error: str | None = "old error"


class _FakeSession:
    """最小化的 async session 桩：支持 get / commit。"""

    def __init__(self, resume: _FakeResume | None) -> None:
        self._resume = resume
        self.commits = 0

    async def get(self, _model: Any, _pk: Any) -> _FakeResume | None:
        return self._resume

    async def commit(self) -> None:
        self.commits += 1


async def test_snapshot_appends_history_and_resets_status():
    resume = _FakeResume(
        parsed_result={
            "profile": {"identity": {"name": "张三"}},
            "classification": {"experience_level": "Mid"},
            "text_blocks": [{"type": "heading", "text": "工作经历", "page": None}],
        },
        parser_version="pdf-parser-v1",
        status=ResumeStatus.EVALUATED.value,
    )
    session = _FakeSession(resume)

    result = await snapshot_and_reset_for_reparse(session, uuid.uuid4())  # type: ignore[arg-type]

    # 状态重置、错误清除
    assert result.status == ResumeStatus.UPLOADED
    assert result.parse_error is None
    assert session.commits == 1

    # 历史追加一条快照，记录版本与旧结果
    history = result.parsed_result["history"]
    assert len(history) == 1
    snap = history[0]
    assert snap["parser_version"] == "pdf-parser-v1"
    assert snap["status"] == ResumeStatus.EVALUATED.value
    assert snap["parsed_result"]["profile"]["identity"]["name"] == "张三"
    # 快照不含 history 自身
    assert "history" not in snap["parsed_result"]


async def test_snapshot_is_idempotent_and_accumulates():
    resume = _FakeResume(
        parsed_result={
            "history": [{"snapshot_at": "2020-01-01T00:00:00+00:00", "parser_version": "v0"}],
            "profile": {"identity": {}},
        },
        parser_version="pdf-parser-v2",
        status=ResumeStatus.CLASSIFIED.value,
    )
    session = _FakeSession(resume)

    result = await snapshot_and_reset_for_reparse(session, uuid.uuid4())  # type: ignore[arg-type]

    history = result.parsed_result["history"]
    # 旧历史保留 + 本次新增 = 2
    assert len(history) == 2
    assert history[0]["parser_version"] == "v0"
    assert history[1]["parser_version"] == "pdf-parser-v2"


async def test_snapshot_missing_resume_raises():
    session = _FakeSession(None)
    with pytest.raises(ValueError):
        await snapshot_and_reset_for_reparse(session, uuid.uuid4())  # type: ignore[arg-type]
