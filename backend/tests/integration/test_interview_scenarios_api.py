"""Interview Scenario registry API tests (AIP-013 #116).

The scenario API is read-only and in-process (no DB), so these tests use
httpx ASGITransport directly against the FastAPI app.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_list_scenarios_returns_seven_active() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    scenarios = body["data"]["scenarios"]
    assert len(scenarios) == 7
    keys = [s["key"] for s in scenarios]
    assert keys == [
        "comprehensive",
        "hr_screen",
        "technical_first",
        "project_deep_dive",
        "system_design",
        "behavioral",
        "manager_round",
    ]
    opts = body["data"]["allowed_global_options"]
    assert opts["durations"] == [15, 30, 45, 60]
    assert opts["difficulties"] == ["basic", "standard", "challenge"]
    assert opts["languages"] == ["zh-CN", "en"]


@pytest.mark.asyncio
async def test_get_scenario_detail_public_fields() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios/comprehensive")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["key"] == "comprehensive"
    assert data["version"] == 1
    assert data["mode"] == "text"
    stage_keys = [s["stage"] for s in data["stages"]]
    assert stage_keys == [
        "introduction",
        "core_skills",
        "project",
        "system_design",
        "behavior",
        "candidate_questions",
    ]
    weights = [s["weight"] for s in data["stages"]]
    assert sum(weights) == 100
    assert data["durations"][0]["main_questions"] == 3
    assert data["durations"][-1]["main_questions"] == 9


@pytest.mark.asyncio
async def test_get_scenario_exact_version() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios/system_design?version=1")
    assert resp.status_code == 200
    assert resp.json()["data"]["version"] == 1


@pytest.mark.asyncio
async def test_get_scenario_not_found() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_scenario_version_not_found() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios/comprehensive?version=99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_detail_has_no_private_fields() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interview-scenarios/behavioral")
    assert resp.status_code == 200
    data = resp.json()["data"]

    def _scan(value, path: str = "") -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                assert k not in ("prompts", "questions", "signals", "rubric", "expected_answer"), (
                    f"{path}.{k} is private"
                )
                _scan(v, f"{path}.{k}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                _scan(item, f"{path}[{i}]")

    _scan(data)
