"""Resume AI Assistant 提案应用事务的 PostgreSQL 集成测试。"""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from backend.application import resume_edit_service
from backend.domain.resume_builder.editing import DraftRevisionConflictError, EditOperation
from backend.infrastructure.db.models import (
    Base,
    ResumeDraftModel,
    ResumeEditProposalModel,
    ResumeEditSessionModel,
)
from backend.tests.conftest import TEST_DB_URL, requires_db

pytestmark = requires_db


@pytest_asyncio.fixture
async def edit_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Keep engine creation, use, and disposal on the test's event loop."""
    schema_name = f"rip006_{uuid.uuid4().hex}"
    admin_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    engine = admin_engine.execution_options(
        schema_translate_map={None: schema_name},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            yield session
            await session.rollback()
    finally:
        async with admin_engine.begin() as connection:
            await connection.execute(
                text(f'DROP SCHEMA "{schema_name}" CASCADE')
            )
        await admin_engine.dispose()


async def _create_proposal(
    session: AsyncSession,
    *,
    revision: int = 1,
) -> tuple[ResumeDraftModel, ResumeEditProposalModel]:
    draft = ResumeDraftModel(
        title=f"RIP-006 integration test {uuid.uuid4()}",
        content={
            "identity": {"name": "张三"},
            "summary": "原简介",
            "sections": [],
        },
        template_id="classic",
        design_tokens={},
        layout_mode="auto_pages",
        target_page_count=None,
        status="draft",
        revision=revision,
    )
    session.add(draft)
    await session.flush()
    conversation = ResumeEditSessionModel(draft_id=draft.id)
    session.add(conversation)
    await session.flush()
    operation = EditOperation(
        kind="replace_summary",
        before="原简介",
        after="三年后端开发经验",
    )
    proposal = ResumeEditProposalModel(
        session_id=conversation.id,
        client_request_id=str(uuid.uuid4()),
        base_revision=1,
        assistant_message="已准备修改。",
        operations=[operation.model_dump(mode="json")],
        status="proposed",
        usage={},
    )
    session.add(proposal)
    await session.commit()
    return draft, proposal


async def test_apply_then_undo_proposal(edit_db_session: AsyncSession) -> None:
    draft, proposal = await _create_proposal(edit_db_session)
    proposal_id = proposal.id
    operation_id = str(proposal.operations[0]["operation_id"])

    applied = await resume_edit_service.apply_proposal(
        edit_db_session,
        draft_id=draft.id,
        proposal_id=proposal_id,
        base_revision=1,
        selected_operation_ids={operation_id},
    )

    assert applied.revision == 2
    assert applied.content["summary"] == "三年后端开发经验"

    undone = await resume_edit_service.undo_proposal(
        edit_db_session,
        draft_id=draft.id,
        proposal_id=proposal_id,
    )

    assert undone.revision == 3
    assert undone.content["summary"] == "原简介"


async def test_stale_proposal_does_not_mutate_draft(
    edit_db_session: AsyncSession,
) -> None:
    draft, proposal = await _create_proposal(edit_db_session, revision=2)
    operation_id = str(proposal.operations[0]["operation_id"])

    with pytest.raises(DraftRevisionConflictError):
        await resume_edit_service.apply_proposal(
            edit_db_session,
            draft_id=draft.id,
            proposal_id=proposal.id,
            base_revision=1,
            selected_operation_ids={operation_id},
        )

    await edit_db_session.refresh(draft)
    assert draft.revision == 2
    assert draft.content["summary"] == "原简介"


async def test_reject_proposal_does_not_mutate_draft(
    edit_db_session: AsyncSession,
) -> None:
    draft, proposal = await _create_proposal(edit_db_session)

    rejected = await resume_edit_service.reject_proposal(
        edit_db_session,
        draft_id=draft.id,
        proposal_id=proposal.id,
    )

    refreshed = await edit_db_session.get(ResumeDraftModel, draft.id)
    assert rejected.status == "rejected"
    assert refreshed is not None
    assert refreshed.revision == 1
    assert refreshed.content["summary"] == "原简介"
