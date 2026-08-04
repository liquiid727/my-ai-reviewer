"""Progress edge cases are deterministic without a database fixture."""

from backend.application.plan_task_service import PlanTaskService


def test_progress_handles_empty_and_completed_collections() -> None:
    assert PlanTaskService._progress_from_statuses([]).model_dump() == {"done": 0, "total": 0, "percent": 0}
    assert PlanTaskService._progress_from_statuses(["done", "todo", "done"]).model_dump() == {
        "done": 2,
        "total": 3,
        "percent": 67,
    }
