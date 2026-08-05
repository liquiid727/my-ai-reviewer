"""Migration tests for immutable JD/Resume input versions (RIP-010 #092).

These run the real Alembic chain against a dedicated migration-test database
so they do not conflict with conftest's ``create_all`` on ``ai_interview_test``.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.tests.conftest import TEST_DB_URL, requires_db

pytestmark = requires_db

MIGRATION_DB_URL = TEST_DB_URL.rsplit("/", 1)[0] + "/ai_interview_migration_test"
_REPO = "/Users/mac_liquiid/Desktop/my-ai-reviewer"

_SKILLS_JSON = (
    '[{"name": "Go", "critical": true, '
    '"evidence": "We need a senior backend engineer with Go and Redis."}]'
)
_STRUCTURED_JSON = (
    '{"title": "Backend Engineer", "required_skills": ['
    '{"name": "Go", "critical": true, '
    '"evidence": "We need a senior backend engineer with Go and Redis."}]}'
)
_RAW_TEXT = "We need a senior backend engineer with Go and Redis."


def _admin_conn_params(url: str) -> dict[str, object]:
    """Parse a postgresql+asyncpg:// URL into asyncpg connect params for the postgres DB."""
    from urllib.parse import urlsplit

    parts = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlsplit(parts)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5433,
        "user": parsed.username or "postgres",
        "password": parsed.password or "postgres",
        "database": "postgres",
    }


def _drop_database(url: str) -> None:
    import asyncpg

    params = _admin_conn_params(url)

    async def _drop() -> None:
        conn = await asyncpg.connect(**params)
        try:
            await conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = 'ai_interview_migration_test' AND pid <> pg_backend_pid()"
            )
            await conn.execute("DROP DATABASE IF EXISTS ai_interview_migration_test")
        finally:
            await conn.close()

    asyncio.run(_drop())


def _create_database(url: str) -> None:
    import asyncpg

    params = _admin_conn_params(url)

    async def _create() -> None:
        conn = await asyncpg.connect(**params)
        try:
            await conn.execute("CREATE DATABASE ai_interview_migration_test")
        finally:
            await conn.close()

    asyncio.run(_create())


def _alembic(target: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", target],
        capture_output=True,
        text=True,
        env={"DATABASE_URL": MIGRATION_DB_URL, "PYTHONPATH": "."},
        cwd=_REPO,
    )
    if proc.returncode != 0:
        raise AssertionError(f"alembic {target} failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


@pytest.fixture(scope="module")
def migration_db() -> Iterator[None]:
    """Fresh dedicated DB migrated to the parent revision; the seed fixture upgrades to head."""
    _drop_database(MIGRATION_DB_URL)
    _create_database(MIGRATION_DB_URL)
    _alembic("o5c6d7e8f9a0")
    # No engine created here — the seed fixture uses raw asyncpg, and tests use
    # a fresh engine created lazily in the pytest-asyncio session loop.
    yield None


@pytest.fixture(scope="module")
def seeded_legacy_db(migration_db: None) -> Iterator[dict[str, uuid.UUID]]:
    """Insert legacy ready/non-ready JDs before the backfill migration runs."""
    import asyncpg

    now = datetime.now(timezone.utc)
    ready_id = uuid.uuid4()
    failed_id = uuid.uuid4()
    conn_params = _admin_conn_params(MIGRATION_DB_URL)
    conn_params["database"] = "ai_interview_migration_test"

    async def _seed() -> None:
        conn = await asyncpg.connect(**conn_params)
        try:
            await conn.execute(
                "INSERT INTO job_descriptions (id, title, company, raw_text, source_type, "
                "required_skills, responsibilities, preferred_skills, seniority, extraction_source, "
                "structured, status, processing_step, content_hash, parser_version, field_sources, "
                "created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, 'text', $5::jsonb, $6::jsonb, $7::jsonb, $8, "
                "'llm', $9::jsonb, 'ready', 'done', $10, $11, $12::jsonb, $13, $13)",
                ready_id,
                "Backend Engineer",
                "Acme",
                _RAW_TEXT,
                _SKILLS_JSON,
                '["Build backend services"]',
                "[]",
                "senior",
                _STRUCTURED_JSON,
                "a" * 64,
                "jd-extractor-v3",
                '{"required_skills": "llm", "title": "llm"}',
                now,
            )
            await conn.execute(
                "INSERT INTO job_descriptions (id, title, raw_text, source_type, required_skills, "
                "responsibilities, preferred_skills, extraction_source, status, processing_step, "
                "field_sources, created_at, updated_at) "
                "VALUES ($1, 'Failed JD', 'bad', 'text', '[]', '[]', '[]', 'manual', "
                "'failed', 'done', '{}', $2, $2)",
                failed_id,
                now,
            )
        finally:
            await conn.close()

    asyncio.run(_seed())
    # Now upgrade through our backfill migration.
    _alembic("head")
    yield {"ready_id": ready_id, "failed_id": failed_id}

    # Module teardown: drop the dedicated DB entirely.
    _drop_database(MIGRATION_DB_URL)


async def _fetch_one(
    engine: Any, sql: str, **params: Any
) -> Any:
    async with engine.connect() as conn:
        return (await conn.execute(text(sql), params)).one()


@pytest.fixture
def migration_engine() -> Iterator[Any]:
    """Async engine bound to the pytest-asyncio session loop for the migration DB."""
    engine = create_async_engine(MIGRATION_DB_URL, echo=False)
    yield engine
    # Teardown runs outside the session loop; dispose on a fresh loop instead of
    # reaching for the already-closed session loop.
    asyncio.new_event_loop().run_until_complete(engine.dispose())


@pytest.mark.asyncio
async def test_ready_jd_backfilled_as_v1(
    seeded_legacy_db: dict[str, uuid.UUID], migration_engine: Any
) -> None:
    row = await _fetch_one(
        migration_engine,
        "SELECT jdv.version_no, jdv.schema_version, jdv.parser_version, jdv.normalized_text, "
        "jdv.content_hash, jdv.evidence, jdv.publication_reason, jd.current_version_id "
        "FROM job_description_versions jdv JOIN job_descriptions jd "
        "ON jd.id = jdv.job_description_id WHERE jd.id = :jd_id",
        jd_id=seeded_legacy_db["ready_id"],
    )
    assert row.version_no == 1
    assert row.schema_version == "jd-v1"
    assert row.parser_version == "jd-extractor-v3"
    assert row.normalized_text == "We need a senior backend engineer with Go and Redis."
    assert row.content_hash == "a" * 64
    assert row.evidence == {"field_sources": {"required_skills": "llm", "title": "llm"}}
    assert row.publication_reason == "legacy_backfill"
    assert row.current_version_id is not None


@pytest.mark.asyncio
async def test_non_ready_jd_not_backfilled(
    seeded_legacy_db: dict[str, uuid.UUID], migration_engine: Any
) -> None:
    async with migration_engine.connect() as conn:
        count = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM job_description_versions WHERE job_description_id = :jd_id"
                ),
                {"jd_id": seeded_legacy_db["failed_id"]},
            )
        ).scalar()
        current = (
            await conn.execute(
                text("SELECT current_version_id FROM job_descriptions WHERE id = :jd_id"),
                {"jd_id": seeded_legacy_db["failed_id"]},
            )
        ).scalar()
    assert count == 0
    assert current is None


@pytest.mark.asyncio
async def test_version_tables_and_columns_exist(
    seeded_legacy_db: dict[str, uuid.UUID], migration_engine: Any
) -> None:
    async with migration_engine.connect() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename IN ('job_description_versions', 'resume_versions')"
                )
            )
        ).fetchall()
        cols = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'job_descriptions' AND column_name = 'current_version_id'"
                )
            )
        ).fetchall()
    assert {t[0] for t in tables} == {"job_description_versions", "resume_versions"}
    assert len(cols) == 1


@pytest.mark.asyncio
async def test_match_assessments_created_by_migration(
    seeded_legacy_db: dict[str, uuid.UUID], migration_engine: Any
) -> None:
    """RIP-013 #109: the migration chain creates match_assessments with its checks/indexes."""
    async with migration_engine.connect() as conn:
        table = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename = 'match_assessments'"
                )
            )
        ).first()
        checks = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'match_assessments'::regclass "
                    "AND contype = 'c' ORDER BY conname"
                )
            )
        ).fetchall()
        indexes = (
            await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'match_assessments' ORDER BY indexname"
                )
            )
        ).fetchall()
        fks = (
            await conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint "
                    "WHERE conrelid = 'match_assessments'::regclass AND contype = 'f'"
                )
            )
        ).fetchall()
        cols = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'match_assessments' "
                    "AND column_name IN ('job_target_id', 'jd_version_id', 'resume_version_id', "
                    "'policy_version', 'run_id', 'attempt', 'error_code', 'error_details', "
                    "'retryable', 'dimension_scores', 'rule_results', 'gaps', 'evidence_summary', "
                    "'caps_applied', 'recommendation', 'score_before_caps', 'total_score', "
                    "'overall_confidence', 'model_name', 'model_version', 'prompt_version', "
                    "'schema_version', 'created_at', 'updated_at', 'completed_at')"
                )
            )
        ).fetchall()
    assert table is not None
    assert {c[0] for c in checks} == {
        "ck_match_assessments_score_before_caps",
        "ck_match_assessments_status",
        "ck_match_assessments_total_score",
        "ck_match_assessments_overall_confidence",
    }
    assert {i[0] for i in indexes} >= {
        "ix_match_assessments_target",
        "ix_match_assessments_jd_version",
        "ix_match_assessments_resume_version",
        "ix_match_assessments_target_created",
        "ix_match_assessments_tuple_created",
        "uq_match_assessments_active_tuple",
        "ix_match_assessments_active_watchdog",
    }
    # every FK is ON DELETE RESTRICT (confdeltype is returned as bytes)
    assert len(fks) == 3
    assert {fk[0].decode() if isinstance(fk[0], bytes) else fk[0] for fk in fks} == {"r"}
    assert len(cols) == 25
