#!/usr/bin/env python3
"""Run local development services and shut down their process groups cleanly."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Sequence
from urllib.error import URLError
from urllib.request import urlopen


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    command: str


@dataclass
class RunningService:
    spec: ServiceSpec
    process: subprocess.Popen[bytes]


def _parse_service(value: str) -> ServiceSpec:
    name, separator, command = value.partition("=")
    if not separator or not name or not command:
        raise argparse.ArgumentTypeError("services must use NAME=COMMAND")
    return ServiceSpec(name=name, command=command)


def _start_services(specs: Sequence[ServiceSpec]) -> list[RunningService]:
    services: list[RunningService] = []
    try:
        for spec in specs:
            process = subprocess.Popen(
                spec.command,
                shell=True,
                start_new_session=True,
            )
            service = RunningService(spec=spec, process=process)
            services.append(service)
            print(f"[dev-services] started {spec.name} (pid {process.pid})", flush=True)
    except OSError:
        _stop_services(services, timeout=1)
        raise
    return services


def _send_to_group(service: RunningService, signum: signal.Signals) -> None:
    if service.process.poll() is not None:
        return
    try:
        os.killpg(service.process.pid, signum)
    except ProcessLookupError:
        return
    except OSError:
        service.process.send_signal(signum)


def _stop_services(services: Sequence[RunningService], timeout: float) -> None:
    active = [service for service in services if service.process.poll() is None]
    for service in active:
        _send_to_group(service, signal.SIGTERM)

    deadline = time.monotonic() + timeout
    while active and time.monotonic() < deadline:
        active = [service for service in active if service.process.poll() is None]
        if active:
            time.sleep(0.05)

    for service in active:
        _send_to_group(service, signal.SIGKILL)

    for service in services:
        service.process.wait()


def _failed_service(services: Sequence[RunningService]) -> RunningService | None:
    for service in services:
        if service.process.poll() is not None:
            return service
    return None


def _wait_for_readiness(
    services: Sequence[RunningService],
    stop_requested: threading.Event,
    url: str,
    timeout: float,
) -> bool:
    deadline = time.monotonic() + timeout
    while not stop_requested.is_set() and time.monotonic() < deadline:
        failed = _failed_service(services)
        if failed is not None:
            raise RuntimeError(
                f"service {failed.spec.name} exited with code {failed.process.returncode}"
            )
        try:
            with urlopen(url, timeout=1):
                return True
        except (OSError, URLError):
            stop_requested.wait(0.25)
    return False


def run_services(
    specs: Sequence[ServiceSpec],
    readiness_url: str | None = None,
    readiness_timeout: float = 40,
    shutdown_timeout: float = 5,
) -> int:
    stop_requested = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_requested.set()

    previous_handlers = {
        signal.SIGINT: signal.getsignal(signal.SIGINT),
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
    }
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    services: list[RunningService] = []
    exit_code = 0
    try:
        services = _start_services(specs)
        if readiness_url:
            if _wait_for_readiness(services, stop_requested, readiness_url, readiness_timeout):
                print(f"[dev-services] ready: {readiness_url}", flush=True)
            elif stop_requested.is_set():
                return 0
            else:
                raise TimeoutError(f"timed out waiting for {readiness_url}")

        while not stop_requested.wait(0.2):
            failed = _failed_service(services)
            if failed is not None:
                exit_code = failed.process.returncode or 1
                print(
                    f"[dev-services] {failed.spec.name} exited with code {failed.process.returncode}",
                    file=sys.stderr,
                    flush=True,
                )
                break
    except (OSError, RuntimeError, TimeoutError) as error:
        print(f"[dev-services] {error}", file=sys.stderr, flush=True)
        exit_code = 1
    finally:
        if services:
            _stop_services(services, timeout=shutdown_timeout)
            print("All services stopped", flush=True)
        signal.signal(signal.SIGINT, previous_handlers[signal.SIGINT])
        signal.signal(signal.SIGTERM, previous_handlers[signal.SIGTERM])
    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service",
        action="append",
        type=_parse_service,
        dest="services",
        metavar="NAME=COMMAND",
        help="service command; repeat for each service",
    )
    parser.add_argument("--ready-url", default=None, help="URL to poll before monitoring services")
    parser.add_argument("--ready-timeout", type=float, default=40)
    parser.add_argument("--shutdown-timeout", type=float, default=5)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.services:
        parser.error("at least one --service is required")
    return run_services(
        args.services,
        readiness_url=args.ready_url,
        readiness_timeout=args.ready_timeout,
        shutdown_timeout=args.shutdown_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
