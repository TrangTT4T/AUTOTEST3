"""Container entry point: run one suite, keep its reports, and tell the truth with the exit code.

    python -m framework.cloud.run_suite --suite offline --artifacts s3://my-bucket/runs

What makes it fit for ECS/Fargate (Unit 4, Days 13 and 15):
* one JSON object per log line (CloudWatch Logs Insights can filter by ``run_id`` and ``event``);
* SIGTERM (what ``StopTask`` and a deployment send, before SIGKILL after ``stopTimeout``)
  is forwarded to pytest, and the reports collected so far are still uploaded;
* the reports are uploaded even when tests fail: failures are when evidence matters most;
* exit code = pytest's (0 passed, 1 failed, 2 interrupted, ...), or 75 if the tests passed
  but the evidence could not be stored: a run without evidence is not a pass.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

from framework.cloud.artifacts import store_from_uri, upload_reports

SUITES: dict[str, list[str]] = {
    "unit": ["tests/unit"],
    "offline": ["--store", "fake", "-n", "auto", "--fail-on-uncovered"],
    "events": ["--store", "fake", "tests/events", "tests/test_order_events.py", "-n", "auto"],
    "web-smoke": ["--store", "web", "-m", "smoke"],  # needs an image with a browser (see docker/README)
}
EXIT_ARTIFACTS_FAILED = 75  # EX_TEMPFAIL: the infrastructure, not the product, failed


def log(event: str, **fields: Any) -> None:
    """One JSON object per line on stdout: the awslogs driver ships each line to CloudWatch Logs."""
    print(
        json.dumps({"time": datetime.now(UTC).isoformat(timespec="milliseconds"), "event": event, **fields}),
        flush=True,
    )


def default_run_id(env: dict[str, str]) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return env.get("RUN_ID") or f"{stamp}-{env.get('GIT_SHA', 'local')[:7]}"


def build_command(suite: str, extra: Sequence[str]) -> list[str]:
    if suite not in SUITES:
        raise ValueError(f"unknown suite {suite!r}; choose one of {sorted(SUITES)}")
    return [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *SUITES[suite], *extra]


def final_exit_code(tests: int, *, artifacts_ok: bool) -> int:
    """Test failures win; otherwise a lost upload turns a pass into an infrastructure failure."""
    if tests != 0:
        return tests
    return 0 if artifacts_ok else EXIT_ARTIFACTS_FAILED


def run(command: Sequence[str], on_signal: Callable[[int], None] | None = None) -> tuple[int, bool]:
    """Run pytest; forward SIGTERM/SIGINT to it. Returns (exit code, interrupted)."""
    child = subprocess.Popen(list(command))  # noqa: S603 - our own fixed command (build_command), no shell
    interrupted = False

    def forward(signum: int, _frame: FrameType | None) -> None:
        nonlocal interrupted
        interrupted = True
        if on_signal:
            on_signal(signum)
        child.send_signal(signal.SIGINT)  # pytest stops cleanly on SIGINT and writes its reports

    previous = {s: signal.signal(s, forward) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        code = child.wait()
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)
    return code, interrupted


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.cloud.run_suite", description=__doc__)
    parser.add_argument("--suite", default=os.getenv("SUITE", "offline"), choices=sorted(SUITES))
    parser.add_argument(
        "--artifacts",
        default=os.getenv("ARTIFACTS", "reports-archive"),
        help="s3://bucket/prefix, file:///path, a path, or 'none'",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("pytest_args", nargs="*", help="extra pytest arguments (after --)")
    args = parser.parse_args(argv)

    run_id = args.run_id or default_run_id(dict(os.environ))
    command = build_command(args.suite, args.pytest_args)
    started = time.monotonic()
    log(
        "run.start",
        run_id=run_id,
        suite=args.suite,
        command=command[1:],
        python=platform.python_version(),
        image=os.getenv("IMAGE_TAG", "unknown"),
    )
    code, interrupted = run(
        command, lambda s: log("run.signal", run_id=run_id, signal=signal.Signals(s).name)
    )
    duration = round(time.monotonic() - started, 1)

    args.reports.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "suite": args.suite,
        "pytest_exit_code": code,
        "interrupted": interrupted,
        "duration_s": duration,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "image": os.getenv("IMAGE_TAG", "unknown"),
        "git_sha": os.getenv("GIT_SHA", "unknown"),
    }
    (args.reports / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    artifacts_ok, location = True, "not stored"
    if args.artifacts != "none":
        try:
            location = upload_reports(store_from_uri(args.artifacts), args.reports, run_id)
        except Exception as error:  # noqa: BLE001 - any storage failure: log it, never hide the test result
            artifacts_ok = False
            log("artifacts.failed", run_id=run_id, error=repr(error))
    exit_code = final_exit_code(code, artifacts_ok=artifacts_ok)
    log(
        "run.end",
        run_id=run_id,
        suite=args.suite,
        pytest_exit_code=code,
        exit_code=exit_code,
        interrupted=interrupted,
        duration_s=duration,
        artifacts=location,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
