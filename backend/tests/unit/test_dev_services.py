import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUPERVISOR = PROJECT_ROOT / "scripts" / "dev_services.py"


def _service_command(pid_file: Path) -> str:
    code = f"import os, pathlib, time; pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
    return shlex.join([sys.executable, "-c", code])


def _wait_for_pid_file(path: Path, process: subprocess.Popen[str]) -> int:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists():
            return int(path.read_text())
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"supervisor exited before starting services: {output}")
        time.sleep(0.05)
    pytest.fail(f"service did not start: {path}")


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_sigint_stops_all_services_and_their_process_groups(tmp_path: Path) -> None:
    pid_files = [tmp_path / "backend.pid", tmp_path / "worker.pid", tmp_path / "frontend.pid"]
    command = [sys.executable, str(SUPERVISOR)]
    for name, pid_file in zip(("backend", "worker", "frontend"), pid_files):
        command.extend(["--service", f"{name}={_service_command(pid_file)}"])

    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    child_pids: list[int] = []
    try:
        child_pids = [_wait_for_pid_file(path, process) for path in pid_files]

        process.send_signal(signal.SIGINT)
        output, _ = process.communicate(timeout=5)

        assert process.returncode == 0, output
        assert "All services stopped" in output
        assert all(not _is_alive(pid) for pid in child_pids)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
