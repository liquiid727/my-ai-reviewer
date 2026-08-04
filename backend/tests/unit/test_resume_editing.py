"""Resume AI Assistant 的结构化提案与白名单操作测试。"""

import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.editing import (
    DraftEditError,
    EditOperation,
    apply_operations,
    materialize_operations,
)
from backend.domain.resume_builder.schemas import DraftItem, DraftSection, ResumeDraft
from backend.infrastructure.editors.llm_resume_editor import LLMResumeEditor
from backend.infrastructure.llm.providers.base import LLMResponse


def _draft() -> ResumeDraft:
    return ResumeDraft(
        title="测试简历",
        identity={"name": "张三", "email": "old@example.com"},
        summary="原简介",
        sections=[
            DraftSection(
                section_id="work",
                section_type=ResumeSectionType.WORK_EXPERIENCE,
                title="工作经历",
                items=[
                    DraftItem(
                        item_id="job-1",
                        heading="某公司",
                        subheading="工程师",
                        bullets=["负责接口开发", "维护线上服务"],
                    ),
                ],
            ),
        ],
    )


def test_materialize_uses_server_before_value() -> None:
    operation = EditOperation(
        kind="replace_bullet",
        section_id="work",
        item_id="job-1",
        bullet_index=0,
        before="模型伪造的原文",
        after="负责核心接口设计与交付",
    )

    materialized = materialize_operations(_draft(), [operation])

    assert materialized[0].before == "负责接口开发"


def test_apply_selected_operations_only() -> None:
    operations = materialize_operations(
        _draft(),
        [
            EditOperation(kind="replace_summary", after="三年后端开发经验"),
            EditOperation(
                kind="replace_identity_field",
                field="email",
                after="new@example.com",
            ),
            EditOperation(
                kind="add_bullet",
                section_id="work",
                item_id="job-1",
                bullet_index=2,
                after="建设监控与告警链路",
            ),
        ],
    )

    selected = {operations[0].operation_id, operations[2].operation_id}
    updated = apply_operations(_draft(), operations, selected)

    assert updated.summary == "三年后端开发经验"
    assert updated.identity["email"] == "old@example.com"
    assert updated.sections[0].items[0].bullets[-1] == "建设监控与告警链路"


def test_apply_rejects_stale_source() -> None:
    operation = materialize_operations(
        _draft(),
        [
            EditOperation(
                kind="replace_bullet",
                section_id="work",
                item_id="job-1",
                bullet_index=0,
                after="新内容",
            ),
        ],
    )[0]
    changed = _draft()
    changed.sections[0].items[0].bullets[0] = "用户刚刚修改的内容"

    with pytest.raises(DraftEditError, match="source no longer matches"):
        apply_operations(changed, [operation], {operation.operation_id})


def test_multiple_bullet_removals_use_original_indexes() -> None:
    operations = materialize_operations(
        _draft(),
        [
            EditOperation(
                kind="remove_bullet",
                section_id="work",
                item_id="job-1",
                bullet_index=0,
            ),
            EditOperation(
                kind="remove_bullet",
                section_id="work",
                item_id="job-1",
                bullet_index=1,
            ),
        ],
    )

    updated = apply_operations(
        _draft(),
        operations,
        {operation.operation_id for operation in operations},
    )

    assert updated.sections[0].items[0].bullets == []


def test_forbidden_identity_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        EditOperation.model_validate(
            {
                "kind": "replace_identity_field",
                "field": "photo",
                "after": "other-object.png",
            }
        )


@pytest.mark.asyncio
async def test_llm_editor_retries_invalid_json() -> None:
    gateway = AsyncMock()
    gateway.complete.side_effect = [
        LLMResponse(content="not-json", model="test-model"),
        LLMResponse(
            content=json.dumps(
                {
                    "assistant_message": "已准备一项修改。",
                    "operations": [
                        {
                            "kind": "replace_summary",
                            "after": "三年后端开发经验",
                            "reason": "更具体",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            model="test-model",
            usage={"prompt_tokens": 20, "completion_tokens": 10},
        ),
    ]

    result = await LLMResumeEditor(gateway).propose(_draft(), "简介写得更具体")

    assert result.operations[0].before == "原简介"
    assert result.model == "test-model"
    assert gateway.complete.await_count == 2
