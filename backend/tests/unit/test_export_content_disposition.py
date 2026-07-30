"""导出端点 Content-Disposition 回归测试 —— 中文标题走 RFC 5987 编码（免数据库）。

背景：starlette 响应头按 latin-1 编码，纯 filename= 携带中文会 UnicodeEncodeError → 500。
修复：filename="resume.pdf" 提供 ASCII 回退 + filename*=UTF-8'' 百分号编码原始标题。
"""

import uuid
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import pytest

from backend.api.v1 import resume_builder as api
from backend.domain.resume_builder.schemas import ExportResult

DRAFT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def patch_export(monkeypatch: pytest.MonkeyPatch):
    """打桩 get_draft / export_draft_pdf，免数据库与 Playwright。"""

    def _patch(title: str) -> None:
        model = SimpleNamespace(title=title)

        async def fake_get_draft(session: Any, draft_id: uuid.UUID) -> Any:
            return model

        async def fake_export_pdf(session: Any, m: Any, options: Any) -> tuple[bytes, ExportResult]:
            return b"%PDF-1.4 fake", ExportResult(page_count=1)

        monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
        monkeypatch.setattr(api.services, "export_draft_pdf", fake_export_pdf)

    return _patch


class TestExportContentDisposition:
    """POST /{draft_id}/export 的响应头。"""

    async def test_chinese_title_rfc5987(self, patch_export) -> None:
        """中文标题 → filename= ASCII 回退 + filename*= 百分号编码，且可按 latin-1 编码。"""
        patch_export("测试草稿035")

        resp = await api.export_draft(DRAFT_ID, api.ExportRequest(), object())

        disposition = resp.headers["content-disposition"]
        expected = f"attachment; filename=\"resume.pdf\"; filename*=UTF-8''{quote('测试草稿035.pdf', safe='')}"
        assert disposition == expected
        # 回归核心：响应头必须能按 latin-1 编码，否则 starlette 序列化时抛 500
        disposition.encode("latin-1")

    async def test_ascii_title_kept_in_extended_param(self, patch_export) -> None:
        """ASCII 标题同样走双参数格式，filename*= 保留原始标题。"""
        patch_export("resume-en")

        resp = await api.export_draft(DRAFT_ID, api.ExportRequest(), object())

        assert (
            resp.headers["content-disposition"]
            == "attachment; filename=\"resume.pdf\"; filename*=UTF-8''resume-en.pdf"
        )
