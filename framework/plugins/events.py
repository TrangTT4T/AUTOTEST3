"""pytest plugin: the order-events sandbox, one flow per test, known defects, and async evidence.

* ``events_sandbox`` (session): one sandbox process per pytest-xdist worker, on a free port,
  logging to ``reports/events/sandbox-<worker>.log`` — or an already running one (``--sandbox-url``).
* ``flow`` / ``flow_factory``: an ``OrderFlow`` with a unique correlation id, subscribed to its
  live status before the test acts.
* ``@pytest.mark.known_defect("D-12-xx")`` (BDD tag ``@defect-D-12-xx``) becomes a strict xfail,
  limited to AssertionError, when the build under test contains the defect (framework/events/findings.py).
* Every events test adds a row to ``reports/events/evidence.md`` (Day 10's template); failing
  and known-defect flows also get their files in ``reports/events/<test>/``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from framework.config import Settings
from framework.events import evidence
from framework.events.client import OrdersClient
from framework.events.correlation import correlation_id
from framework.events.findings import active
from framework.events.flow import OrderFlow
from framework.events.model import SandboxInfo
from framework.events.process import SandboxProcess

ROW_KEY = "events_row"
_CALL = pytest.StashKey[pytest.TestReport]()
_ROW = pytest.StashKey[dict[str, str]]()
_SCENARIO = pytest.StashKey[str]()
_ROWS: list[dict[str, str]] = []


@dataclass(frozen=True)
class Sandbox:
    client: OrdersClient
    info: SandboxInfo
    log_path: Path | None


# ------------------------------------------------------------------------- known defects
def _defect_ids(item: pytest.Item) -> list[str]:
    return [str(marker.args[0]) for marker in item.iter_markers("known_defect")]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    build = str(config.getoption("sandbox_build"))
    for item in items:
        for defect_id in _defect_ids(item):
            try:
                finding = active(defect_id, build)
            except KeyError:
                raise pytest.UsageError(
                    f"{item.nodeid}: unknown defect {defect_id!r} - register it in "
                    "framework/events/findings.py"
                ) from None
            if finding is not None:
                item.add_marker(
                    pytest.mark.xfail(
                        strict=True,
                        raises=AssertionError,  # only the documented failure counts; anything else surfaces
                        reason=f"{finding.id} ({finding.severity}): {finding.title} [build {build}]",
                    )
                )


# ------------------------------------------------------------------------------ fixtures
@pytest.fixture(scope="session")
def events_sandbox(settings: Settings, pytestconfig: pytest.Config, worker_id: str) -> Iterator[Sandbox]:
    if settings.sandbox_url:
        client = OrdersClient(settings.sandbox_url)
        info = client.info()
        if info.build != settings.sandbox_build:
            pytest.fail(
                f"--sandbox-url runs build {info.build!r} but --sandbox-build says "
                f"{settings.sandbox_build!r}: "
                "the known-defect marks would be wrong",
                pytrace=False,
            )
        yield Sandbox(client, info, None)
        return
    log_path = Path(pytestconfig.rootpath, "reports", "events", f"sandbox-{worker_id}.log")
    process = SandboxProcess(pytestconfig.rootpath, settings.sandbox_build, log_path)
    url = process.start()
    try:
        client = OrdersClient(url)
        yield Sandbox(client, client.info(), log_path)
    finally:
        process.stop()


@pytest.fixture
def flow_factory(
    request: pytest.FixtureRequest, events_sandbox: Sandbox, testrun_uid: str, worker_id: str
) -> Iterator[Callable[[str], OrderFlow]]:
    """``make(label)``: another flow in the same test, e.g. a second customer."""
    flows: list[OrderFlow] = []

    def make(label: str = "") -> OrderFlow:
        cid = correlation_id(testrun_uid, worker_id, request.node.nodeid, label)
        flow = OrderFlow(events_sandbox.client, events_sandbox.info, cid)
        flow.follow()
        flows.append(flow)
        return flow

    yield make

    report = request.node.stash.get(_CALL, None)
    if report is not None and (report.failed or hasattr(report, "wasxfail")):
        base = Path(request.config.rootpath, "reports", "events", _slug(request.node.name))
        for flow in flows:
            folder = base / _slug(flow.correlation_id.rsplit("-", 1)[-1]) if len(flows) > 1 else base
            written = evidence.collect(flow, folder, events_sandbox.log_path)
            if written:
                request.node.add_report_section("teardown", "events evidence", f"{folder}")
    row = evidence.row(_test_name(request.node), _oracle(request.node), flows, _result(request.node, report))
    row["_target"] = f"{events_sandbox.info.consistency_target:g} s"
    request.node.stash[_ROW] = row
    for flow in flows:
        flow.close()


@pytest.fixture
def flow(flow_factory: Callable[[str], OrderFlow]) -> OrderFlow:
    """This test's order flow, already following its live status."""
    return flow_factory("")


# ------------------------------------------------------------------------------- evidence
def pytest_bdd_before_scenario(request: pytest.FixtureRequest, feature: Any, scenario: Any) -> None:
    thens = [step.name for step in scenario.steps if step.type == "then"]
    request.node.stash[_SCENARIO] = "; ".join(thens)


@pytest.hookimpl(wrapper=True, tryfirst=True)  # outermost: sees the final report (xfail applied)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if report.when == "call":
        item.stash[_CALL] = report
    elif report.when == "teardown" and _ROW in item.stash:
        report.user_properties.append((ROW_KEY, json.dumps(item.stash[_ROW])))
    return report


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    for key, value in report.user_properties:
        if key == ROW_KEY:
            _ROWS.append(json.loads(str(value)))


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, config: pytest.Config) -> None:
    if not _ROWS or hasattr(config, "workerinput"):
        return
    url = config.getoption("sandbox_url")
    header = {
        "System under test": f"order-events sandbox, build `{config.getoption('sandbox_build')}`",
        "Endpoint": url or "local process per pytest worker (`python -m sandbox --port 0`), HTTP + WebSocket",
        "Consistency target": _ROWS[0].get("_target", "-"),
        "Correlation ids": "`T-<run>-<worker>-<test>-<hash>`, one per flow",
        "Injected faults": "per test, scoped to its correlation id (column Fault)",
    }
    path = Path(config.rootpath, "reports", "events", "evidence.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(evidence.to_markdown(_ROWS, header), encoding="utf-8")
    terminalreporter.write_line(
        f"Async execution evidence: {path.relative_to(config.rootpath)} ({len(_ROWS)} tests)"
    )


def _slug(text: str) -> str:
    return re.sub(r"\W+", "_", text).strip("_")[:100]


def _test_name(item: pytest.Item) -> str:
    return f"{item.path.stem}::{item.name}"


def _oracle(item: pytest.Item) -> str:
    if _SCENARIO in item.stash:
        return item.stash[_SCENARIO]
    doc = getattr(getattr(item, "function", None), "__doc__", None) or ""
    return doc.strip().splitlines()[0] if doc.strip() else "-"


def _result(item: pytest.Item, report: pytest.TestReport | None) -> str:
    if report is None:
        return "NOT RUN (setup failed)"
    if hasattr(report, "wasxfail"):
        return "XFAIL " + ", ".join(_defect_ids(item))
    if report.passed:
        return "PASS"
    if "XPASS(strict)" in str(report.longrepr):
        return "FAIL (XPASS strict: defect gone? update findings.py)"
    if dict(report.user_properties).get("shop_outcome") == "blocked":
        return "BLOCKED"
    return "FAIL"
