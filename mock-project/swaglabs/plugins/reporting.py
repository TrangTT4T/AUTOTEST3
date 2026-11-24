"""pytest plugin: structured logs, traceability, timings, the run record and the manifest.

Works with pytest-xdist: outcome classes and measurements travel inside the test reports
(``user_properties``) to the controller, which alone writes the run-level files.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from collections import Counter
from collections.abc import Generator
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

from swaglabs.config import Settings
from swaglabs.evidence import JsonLineFormatter, RedactingFilter, run_record, write_manifest
from swaglabs.perf import Measurement, load_budgets, summarise
from swaglabs.perf import to_markdown as perf_markdown
from swaglabs.plugins.browser import PERF_PROPERTY
from swaglabs.plugins.registry import registry_of, scenarios_of
from swaglabs.requirements import requirement_tags
from swaglabs.traceability import build_matrix, requirement_index
from swaglabs.traceability import to_markdown as trace_markdown

STARTED_KEY = pytest.StashKey[datetime]()
STATE_KEY = pytest.StashKey["RunState"]()
ROWS_KEY = pytest.StashKey[list[tuple[str, str]]]()
CI_VARIABLES = ("GITHUB_SHA", "GITHUB_REF_NAME", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW")
PACKAGES = ("pytest", "pytest-bdd", "playwright", "pytest-playwright", "pytest-xdist")


class RunState:
    def __init__(self) -> None:
        self.results: dict[str, tuple[list[str], str]] = {}
        self.outcomes: Counter[str] = Counter()
        self.known_defects: set[str] = set()
        self.measurements: list[Measurement] = []
        self.handler: logging.Handler | None = None


def reports_dir(config: pytest.Config) -> Path:
    return Path(config.rootpath, "reports")


def pytest_configure(config: pytest.Config) -> None:
    state = RunState()
    config.stash[STATE_KEY] = state
    config.stash[STARTED_KEY] = datetime.now(tz=UTC)
    if config.option.collectonly:
        return
    # One JSON log per process (xdist workers write in parallel): no interleaved lines.
    worker = getattr(config, "workerinput", {}).get("workerid", "main")
    folder = reports_dir(config)
    password = Settings.from_pytest(config).password
    try:
        folder.mkdir(exist_ok=True)
        handler = logging.FileHandler(folder / f"log-{worker}.jsonl", encoding="utf-8")
    except OSError as error:
        # Fail before any test runs: a run whose evidence cannot be written is not worth starting.
        raise pytest.UsageError(
            f"cannot write evidence to {folder} ({error.strerror}); in a read-only container mount "
            'a volume or tmpfs there, e.g. -v "$PWD/reports:/work/reports"'
        ) from error
    handler.setFormatter(JsonLineFormatter(secrets=[password], static={"worker": worker}))
    handler.addFilter(RedactingFilter([password]))
    handler.setLevel(logging.INFO)
    logging.getLogger("swaglabs").addHandler(handler)
    logging.getLogger("swaglabs").setLevel(logging.INFO)
    state.handler = handler


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    defects = sorted(m.args[0] for m in item.iter_markers("known_defect"))
    if defects and call.when == "call":  # counted only if the report turns out to be an xfail
        report.user_properties.append(("known_defects", defects))
    return report


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    config_state = _STATE.get("state")
    if config_state is None:
        return
    properties: dict[str, Any] = dict(report.user_properties)
    if report.when == "teardown":
        config_state.measurements += [Measurement.from_dict(m) for m in properties.get(PERF_PROPERTY, [])]
    if not (report.when == "call" or (report.when == "setup" and not report.passed)):
        return
    outcome: str = report.outcome
    if hasattr(report, "wasxfail") and report.when == "call":
        outcome = "known-defect"  # an xfail report says "skipped": counting it as manual would hide a defect
        config_state.known_defects.update(properties.get("known_defects", []))
    config_state.outcomes[outcome] += 1
    reqs = requirement_tags(report.keywords)
    if reqs:
        config_state.results[report.nodeid] = (reqs, str(outcome))


# pytest_runtest_logreport receives no config: keep a module-level pointer to this run's state.
_STATE: dict[str, RunState] = {}


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    _STATE["state"] = session.config.stash[STATE_KEY]


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    config = session.config
    state = config.stash[STATE_KEY]
    if state.handler is not None:
        logging.getLogger("swaglabs").removeHandler(state.handler)
        state.handler.close()
    if hasattr(config, "workerinput") or config.option.collectonly or not state.outcomes:
        return
    if not state.results:  # only unit tests ran: no run-level BDD reports, nothing to trace
        return
    settings = Settings.from_pytest(config)
    folder = reports_dir(config)
    _write_traceability(config, state, settings, folder)
    _write_perf(config, state, settings, folder)
    (folder / "run.json").write_text(
        json.dumps(_run_record(config, state, settings), indent=2), encoding="utf-8"
    )
    write_manifest(folder)  # LAST: it fingerprints everything written above


def _write_traceability(config: pytest.Config, state: RunState, settings: Settings, folder: Path) -> None:
    rows = build_matrix(registry_of(config), requirement_index(scenarios_of(config)), state.results.values())
    title = f"Traceability - {settings.label}"
    (folder / "traceability.md").write_text(trace_markdown(rows, title), encoding="utf-8")
    payload = {
        "label": settings.label,
        "settings": settings.public(),
        "known_defects": sorted(state.known_defects),
        "rows": [row.as_dict() for row in rows],
    }
    (folder / "traceability.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    config.stash[ROWS_KEY] = [(r.requirement.id, r.status) for r in rows]


def _write_perf(config: pytest.Config, state: RunState, settings: Settings, folder: Path) -> None:
    budgets = load_budgets(Path(config.rootpath, str(config.getini("perf_budgets"))))
    stats = summarise(state.measurements, budgets)
    (folder / "perf.md").write_text(perf_markdown(stats, settings.label), encoding="utf-8")
    (folder / "perf.json").write_text(
        json.dumps(
            {"label": settings.label, "measurements": [m.as_dict() for m in state.measurements]}, indent=2
        ),
        encoding="utf-8",
    )


def _run_record(config: pytest.Config, state: RunState, settings: Settings) -> dict[str, Any]:
    versions = {name: metadata.version(name) for name in PACKAGES}
    versions["python"] = platform.python_version()
    return run_record(
        settings={
            **settings.public(),
            "workers": config.getoption("numprocesses", None) or 0,
            "versions": versions,
        },
        outcomes=state.outcomes,
        started=config.stash[STARTED_KEY],
        finished=datetime.now(tz=UTC),
        environment={k: v for k in CI_VARIABLES if (v := os.getenv(k))},
    )


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, config: pytest.Config) -> None:
    rows = config.stash.get(ROWS_KEY, None)
    if not rows:
        return
    terminalreporter.section("Requirement traceability")
    for req_id, status in rows:
        terminalreporter.write_line(f"{req_id:<10} {status}")
    state = config.stash[STATE_KEY]
    if state.known_defects:
        terminalreporter.write_line(f"Known defects reproduced: {', '.join(sorted(state.known_defects))}")
    terminalreporter.write_line(f"Reports: {reports_dir(config).relative_to(config.rootpath)}/")
