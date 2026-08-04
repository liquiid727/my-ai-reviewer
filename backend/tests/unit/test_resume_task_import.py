"""The Celery resume task module must be importable in a fresh process."""

from __future__ import annotations

import os
import subprocess
import sys


def test_resume_tasks_import_without_application_cycle() -> None:
    env = {**os.environ, "PYTHONPATH": "."}
    result = subprocess.run(
        [sys.executable, "-c", "import backend.tasks.resume_tasks"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
