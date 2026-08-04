"""AI 简历编辑提案契约与白名单操作。"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.domain.resume_builder.schemas import DraftItem, DraftSection, ResumeDraft

EditKind = Literal[
    "replace_summary",
    "replace_identity_field",
    "replace_item_field",
    "replace_bullet",
    "add_bullet",
    "remove_bullet",
]
IdentityField = Literal["name", "email", "phone", "location"]
ItemField = Literal["heading", "subheading", "date_range"]


class EditOperation(BaseModel):
    """模型可提出的单项修改；目标字段由 kind 和稳定 ID 共同约束。"""

    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: EditKind
    section_id: str | None = None
    item_id: str | None = None
    bullet_index: int | None = Field(default=None, ge=0)
    field: IdentityField | ItemField | None = None
    before: str | None = None
    after: str | None = Field(default=None, max_length=4000)
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_target(self) -> "EditOperation":
        if self.kind == "replace_summary":
            if any((self.section_id, self.item_id, self.bullet_index is not None, self.field)):
                raise ValueError("replace_summary cannot target a section or field")
        elif self.kind == "replace_identity_field":
            if self.field not in {"name", "email", "phone", "location"}:
                raise ValueError("invalid identity field")
            if any((self.section_id, self.item_id, self.bullet_index is not None)):
                raise ValueError("identity edits cannot target a section")
        elif self.kind == "replace_item_field":
            if not self.section_id or not self.item_id:
                raise ValueError("item edits require section_id and item_id")
            if self.field not in {"heading", "subheading", "date_range"}:
                raise ValueError("invalid item field")
            if self.bullet_index is not None:
                raise ValueError("item field edits cannot target a bullet")
        else:
            if not self.section_id or not self.item_id or self.bullet_index is None:
                raise ValueError("bullet edits require section_id, item_id and bullet_index")
            if self.field is not None:
                raise ValueError("bullet edits cannot set field")

        if self.kind != "remove_bullet" and self.after is None:
            raise ValueError("operation requires after")
        if self.kind == "remove_bullet" and self.after is not None:
            raise ValueError("remove_bullet cannot set after")
        return self


class EditProposalResult(BaseModel):
    """一次 LLM 调用产出的、尚未落库的提案。"""

    assistant_message: str = Field(min_length=1, max_length=4000)
    operations: list[EditOperation] = Field(default_factory=list, max_length=30)
    model: str
    usage: dict[str, object] = Field(default_factory=dict)


class DraftEditError(ValueError):
    """结构化操作无法安全定位或应用。"""


class DraftRevisionConflictError(ValueError):
    """草稿版本已变化，调用方必须重新生成或应用提案。"""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"Draft revision conflict: expected {expected}, actual {actual}")
        self.expected = expected
        self.actual = actual


def materialize_operations(draft: ResumeDraft, operations: list[EditOperation]) -> list[EditOperation]:
    """解析稳定 ID，并以服务端当前值填充 before，拒绝模型伪造原文。"""

    materialized: list[EditOperation] = []
    for operation in operations:
        op = operation.model_copy(deep=True)
        if op.kind == "replace_summary":
            op.before = draft.summary or ""
        elif op.kind == "replace_identity_field":
            op.before = str(draft.identity.get(str(op.field)) or "")
        else:
            _, item = _find_item(draft, op.section_id, op.item_id)
            if op.kind == "replace_item_field":
                op.before = str(getattr(item, str(op.field)) or "")
            elif op.kind == "add_bullet":
                if op.bullet_index is None or op.bullet_index > len(item.bullets):
                    raise DraftEditError("add_bullet index is out of range")
                op.before = None
            else:
                if op.bullet_index is None or op.bullet_index >= len(item.bullets):
                    raise DraftEditError("bullet index is out of range")
                op.before = item.bullets[op.bullet_index]
        materialized.append(op)
    return materialized


def apply_operations(
    draft: ResumeDraft,
    operations: list[EditOperation],
    selected_operation_ids: set[str],
) -> ResumeDraft:
    """在草稿副本上应用选中操作；调用方负责 revision 的原子持久化。"""

    next_draft = draft.model_copy(deep=True)
    selected_operations = [
        operation for operation in operations if operation.operation_id in selected_operation_ids
    ]
    # 结构性 bullet 操作按原始下标倒序执行，避免前一项插入/删除改变后一项目标。
    selected_operations.sort(
        key=lambda operation: (
            {"remove_bullet": 1, "add_bullet": 2}.get(operation.kind, 0),
            operation.section_id or "",
            operation.item_id or "",
            -(operation.bullet_index or 0),
        ),
    )
    for operation in selected_operations:
        op = materialize_operations(next_draft, [operation])[0]
        if operation.before != op.before:
            raise DraftEditError("operation source no longer matches the draft")

        if op.kind == "replace_summary":
            next_draft.summary = op.after
        elif op.kind == "replace_identity_field":
            next_draft.identity[str(op.field)] = op.after or ""
        else:
            section, item = _find_item(next_draft, op.section_id, op.item_id)
            if op.kind == "replace_item_field":
                setattr(item, str(op.field), op.after)
            elif op.kind == "replace_bullet":
                item.bullets[op.bullet_index or 0] = op.after or ""
            elif op.kind == "add_bullet":
                item.bullets.insert(op.bullet_index or 0, op.after or "")
            else:
                item.bullets.pop(op.bullet_index or 0)
            _replace_item(next_draft, section, item)
    return next_draft


def _find_item(
    draft: ResumeDraft,
    section_id: str | None,
    item_id: str | None,
) -> tuple[DraftSection, DraftItem]:
    section = next((candidate for candidate in draft.sections if candidate.section_id == section_id), None)
    if section is None:
        raise DraftEditError("section not found")
    item = next((candidate for candidate in section.items if candidate.item_id == item_id), None)
    if item is None:
        raise DraftEditError("item not found")
    return section, item


def _replace_item(draft: ResumeDraft, section: DraftSection, item: DraftItem) -> None:
    """将已修改的嵌套模型显式写回，避免依赖 Pydantic 容器实现细节。"""

    section_index = next(i for i, candidate in enumerate(draft.sections) if candidate.section_id == section.section_id)
    item_index = next(i for i, candidate in enumerate(section.items) if candidate.item_id == item.item_id)
    draft.sections[section_index].items[item_index] = item
