"""Resume Builder AI 助手用例编排。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.resume_builder import services as draft_services
from backend.domain.resume_builder.editing import (
    DraftRevisionConflictError,
    EditOperation,
    apply_operations,
)
from backend.infrastructure.db.models import (
    LLMConfigModel,
    ResumeDraftModel,
    ResumeEditMessageModel,
    ResumeEditProposalModel,
    ResumeEditSessionModel,
)
from backend.infrastructure.editors import LLMResumeEditor
from backend.infrastructure.llm.gateway import LLMGateway


class ProposalStateError(ValueError):
    """提案状态不允许当前动作。"""


async def propose_edit(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    base_revision: int,
    instruction: str,
    client_request_id: str,
    llm_config: LLMConfigModel,
    conversation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """生成并持久化一个提案，但不修改草稿。"""

    existing = await session.scalar(
        select(ResumeEditProposalModel).where(
            ResumeEditProposalModel.client_request_id == client_request_id,
        ),
    )
    if existing is not None:
        existing_session = await session.get(ResumeEditSessionModel, existing.session_id)
        if existing_session is None or existing_session.draft_id != draft_id:
            raise ValueError("client_request_id belongs to another draft")
        return await get_conversation(session, draft_id=draft_id, conversation_id=existing.session_id)

    draft_model = await draft_services.get_draft(session, draft_id)
    if draft_model.revision != base_revision:
        raise DraftRevisionConflictError(base_revision, draft_model.revision)

    conversation = await _resolve_conversation(
        session,
        draft_id=draft_id,
        conversation_id=conversation_id,
        llm_config_id=llm_config.id,
        create=False,
    )
    gateway = LLMGateway.from_config(llm_config)
    result = await LLMResumeEditor(gateway).propose(
        draft_services.draft_model_to_schema(draft_model),
        instruction,
    )

    if conversation is None:
        conversation = ResumeEditSessionModel(
            draft_id=draft_id,
            llm_config_id=llm_config.id,
            status="active",
        )
        session.add(conversation)
        await session.flush()
    else:
        conversation.llm_config_id = llm_config.id

    max_sequence = await session.scalar(
        select(func.coalesce(func.max(ResumeEditMessageModel.sequence), 0)).where(
            ResumeEditMessageModel.session_id == conversation.id,
        ),
    )
    sequence = int(max_sequence or 0)
    session.add_all(
        [
            ResumeEditMessageModel(
                session_id=conversation.id,
                sequence=sequence + 1,
                role="user",
                content=instruction,
            ),
            ResumeEditMessageModel(
                session_id=conversation.id,
                sequence=sequence + 2,
                role="assistant",
                content=result.assistant_message,
            ),
        ]
    )
    proposal = ResumeEditProposalModel(
        session_id=conversation.id,
        client_request_id=client_request_id,
        base_revision=base_revision,
        assistant_message=result.assistant_message,
        operations=[operation.model_dump(mode="json") for operation in result.operations],
        status="proposed",
        model_name=result.model,
        usage=result.usage,
    )
    session.add(proposal)
    await session.commit()
    return await get_conversation(session, draft_id=draft_id, conversation_id=conversation.id)


async def get_latest_conversation(session: AsyncSession, *, draft_id: uuid.UUID) -> dict[str, Any] | None:
    conversation_id = await session.scalar(
        select(ResumeEditSessionModel.id)
        .where(ResumeEditSessionModel.draft_id == draft_id)
        .order_by(ResumeEditSessionModel.updated_at.desc(), ResumeEditSessionModel.created_at.desc())
        .limit(1),
    )
    if conversation_id is None:
        return None
    return await get_conversation(session, draft_id=draft_id, conversation_id=conversation_id)


async def get_conversation(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> dict[str, Any]:
    conversation = await session.get(ResumeEditSessionModel, conversation_id)
    if conversation is None or conversation.draft_id != draft_id:
        raise ValueError("Resume edit conversation not found")

    messages = list(
        (
            await session.scalars(
                select(ResumeEditMessageModel)
                .where(ResumeEditMessageModel.session_id == conversation_id)
                .order_by(ResumeEditMessageModel.sequence.asc()),
            )
        ).all()
    )
    proposals = list(
        (
            await session.scalars(
                select(ResumeEditProposalModel)
                .where(ResumeEditProposalModel.session_id == conversation_id)
                .order_by(ResumeEditProposalModel.created_at.asc()),
            )
        ).all()
    )
    return {
        "conversation_id": str(conversation.id),
        "status": conversation.status,
        "messages": [_serialize_message(message) for message in messages],
        "proposals": [_serialize_proposal(proposal) for proposal in proposals],
    }


async def apply_proposal(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
    base_revision: int,
    selected_operation_ids: set[str],
) -> ResumeDraftModel:
    proposal, conversation = await _get_proposal(session, draft_id, proposal_id)
    if proposal.status != "proposed":
        raise ProposalStateError(f"Proposal is already {proposal.status}")
    if proposal.base_revision != base_revision:
        raise DraftRevisionConflictError(base_revision, proposal.base_revision)

    operation_models = [EditOperation.model_validate(operation) for operation in proposal.operations]
    allowed_ids = {operation.operation_id for operation in operation_models}
    if not selected_operation_ids or not selected_operation_ids.issubset(allowed_ids):
        raise ValueError("selected_operation_ids must select proposal operations")

    draft_model = await draft_services.get_draft(session, draft_id)
    if draft_model.revision != base_revision:
        raise DraftRevisionConflictError(base_revision, draft_model.revision)
    before_content = dict(draft_model.content or {})
    draft = draft_services.draft_model_to_schema(draft_model)
    next_draft = apply_operations(draft, operation_models, selected_operation_ids)
    after_content = draft_services._draft_content(next_draft)

    new_revision = await session.scalar(
        update(ResumeDraftModel)
        .where(ResumeDraftModel.id == draft_id, ResumeDraftModel.revision == base_revision)
        .values(
            content=after_content,
            revision=ResumeDraftModel.revision + 1,
            updated_at=func.now(),
        )
        .returning(ResumeDraftModel.revision),
    )
    if new_revision is None:
        await session.rollback()
        actual = await session.scalar(select(ResumeDraftModel.revision).where(ResumeDraftModel.id == draft_id))
        raise DraftRevisionConflictError(base_revision, int(actual or 0))

    proposal.status = "applied"
    proposal.selected_operation_ids = sorted(selected_operation_ids)
    proposal.before_content = before_content
    proposal.after_content = after_content
    proposal.applied_revision = int(new_revision)
    proposal.applied_at = datetime.now(UTC)
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    session.expire_all()
    return await draft_services.get_draft(session, draft_id)


async def reject_proposal(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> ResumeEditProposalModel:
    proposal, conversation = await _get_proposal(session, draft_id, proposal_id)
    if proposal.status != "proposed":
        raise ProposalStateError(f"Proposal is already {proposal.status}")
    proposal.status = "rejected"
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(proposal)
    return proposal


async def undo_proposal(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> ResumeDraftModel:
    proposal, conversation = await _get_proposal(session, draft_id, proposal_id)
    if proposal.status != "applied" or proposal.before_content is None or proposal.applied_revision is None:
        raise ProposalStateError("Only an applied proposal can be undone")

    new_revision = await session.scalar(
        update(ResumeDraftModel)
        .where(
            ResumeDraftModel.id == draft_id,
            ResumeDraftModel.revision == proposal.applied_revision,
        )
        .values(
            content=proposal.before_content,
            revision=ResumeDraftModel.revision + 1,
            updated_at=func.now(),
        )
        .returning(ResumeDraftModel.revision),
    )
    if new_revision is None:
        await session.rollback()
        actual = await session.scalar(select(ResumeDraftModel.revision).where(ResumeDraftModel.id == draft_id))
        raise DraftRevisionConflictError(proposal.applied_revision, int(actual or 0))

    proposal.status = "undone"
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    session.expire_all()
    return await draft_services.get_draft(session, draft_id)


async def _resolve_conversation(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    llm_config_id: uuid.UUID,
    create: bool,
) -> ResumeEditSessionModel | None:
    if conversation_id is not None:
        conversation = await session.get(ResumeEditSessionModel, conversation_id)
        if conversation is None or conversation.draft_id != draft_id:
            raise ValueError("Resume edit conversation not found")
        return conversation
    if not create:
        return None
    conversation = ResumeEditSessionModel(draft_id=draft_id, llm_config_id=llm_config_id)
    session.add(conversation)
    await session.flush()
    return conversation


async def _get_proposal(
    session: AsyncSession,
    draft_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> tuple[ResumeEditProposalModel, ResumeEditSessionModel]:
    proposal = await session.get(ResumeEditProposalModel, proposal_id)
    if proposal is None:
        raise ValueError("Resume edit proposal not found")
    conversation = await session.get(ResumeEditSessionModel, proposal.session_id)
    if conversation is None or conversation.draft_id != draft_id:
        raise ValueError("Resume edit proposal not found")
    return proposal, conversation


def _serialize_message(message: ResumeEditMessageModel) -> dict[str, Any]:
    return {
        "message_id": str(message.id),
        "sequence": message.sequence,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _serialize_proposal(proposal: ResumeEditProposalModel) -> dict[str, Any]:
    return {
        "proposal_id": str(proposal.id),
        "base_revision": proposal.base_revision,
        "assistant_message": proposal.assistant_message,
        "operations": proposal.operations,
        "selected_operation_ids": proposal.selected_operation_ids,
        "status": proposal.status,
        "model": proposal.model_name,
        "usage": proposal.usage,
        "applied_revision": proposal.applied_revision,
        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
    }
