"""Job Target concurrency and invariant integration tests (RIP-010 #093)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.db.models import JobTargetModel
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _insert_jd(session: AsyncSession) -> uuid.UUID:
    from backend.infrastructure.db.models import JobDescriptionModel

    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Concurrent JD",
        raw_text="Some JD",
        status="ready",
        processing_step="done",
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return jd.id


async def test_partial_unique_index_prevents_duplicate_active_target(
    db_session: AsyncSession,
) -> None:
    """Two inserts of an active target for the same JD cannot both succeed."""
    jd_id = await _insert_jd(db_session)

    first = JobTargetModel(id=uuid.uuid4(), job_description_id=jd_id, revision=1)
    db_session.add(first)
    await db_session.commit()

    # Second active target for the same JD violates the partial unique index.
    second = JobTargetModel(id=uuid.uuid4(), job_description_id=jd_id, revision=1)
    db_session.add(second)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_concurrent_active_target_inserts_leave_one_row(
    db_session: AsyncSession,
) -> None:
    """Concurrent inserts of active targets for the same JD leave exactly one row."""
    jd_id = await _insert_jd(db_session)
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()

    async def _insert(tid: uuid.UUID) -> bool:
        from backend.tests.conftest import TestSessionFactory

        async with TestSessionFactory() as session:
            try:
                session.add(JobTargetModel(id=tid, job_description_id=jd_id, revision=1))
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False

    results = await asyncio.gather(_insert(id_a), _insert(id_b))
    assert sum(results) == 1, f"expected exactly one success, got {results}"

    rows = (
        await db_session.execute(
            select(JobTargetModel.id).where(JobTargetModel.job_description_id == jd_id)
        )
    ).scalars().all()
    assert len(rows) == 1


async def test_archived_target_does_not_block_new_active_target(
    db_session: AsyncSession,
) -> None:
    """Archiving a target frees the partial unique index for a new active target."""
    from datetime import datetime, timezone

    jd_id = await _insert_jd(db_session)

    first = JobTargetModel(id=uuid.uuid4(), job_description_id=jd_id, revision=1)
    db_session.add(first)
    await db_session.commit()

    # Archive the first target; this releases the partial unique slot.
    first.archived_at = datetime.now(timezone.utc)
    first.revision = 2
    await db_session.commit()

    second = JobTargetModel(id=uuid.uuid4(), job_description_id=jd_id, revision=1)
    db_session.add(second)
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(JobTargetModel.id, JobTargetModel.archived_at)
            .where(JobTargetModel.job_description_id == jd_id)
            .order_by(JobTargetModel.created_at)
        )
    ).all()
    assert len(rows) == 2
    assert rows[0].archived_at is not None
    assert rows[1].archived_at is None
