"""pytest plugin: classify outcomes and print the traceability matrix.

Works with pytest-xdist: the outcome class travels inside each test report
(``user_properties``), which workers send to the main process.
"""

from __future__ import annotations

import csv
from collections.abc import Generator
from pathlib import Path

import pytest

from framework.errors import EnvironmentBlockedError
from framework.plugins.tags import registry_of
from framework.traceability import HEADER, build_matrix, declared_scenarios, to_markdown

_RESULTS: dict[str, tuple[list[str], str]] = {}
OUTCOME_KEY = "shop_outcome"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if call.excinfo is not None and call.excinfo.errisinstance(EnvironmentBlockedError):
        report.user_properties.append((OUTCOME_KEY, "blocked"))
    return report


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not (report.when == "call" or (report.when == "setup" and not report.passed)):
        return
    reqs = sorted(k for k in report.keywords if k.startswith("REQ-"))
    if not reqs:
        return
    outcome = dict(report.user_properties).get(OUTCOME_KEY, report.outcome)
    if hasattr(report, "wasxfail") and report.when == "call":
        outcome = "known-defect"  # xfail reports say "skipped"; counting them as manual would hide a defect
    _RESULTS[report.nodeid] = (reqs, str(outcome))


def _features_dir(config: pytest.Config) -> Path:
    return Path(config.rootpath, str(config.getini("bdd_features_base_dir")))


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, config: pytest.Config) -> None:
    if not _RESULTS:  # no BDD scenario ran (e.g. only unit tests): nothing to trace
        return
    rows = build_matrix(registry_of(config), declared_scenarios(_features_dir(config)), _RESULTS.values())

    terminalreporter.section("Requirement traceability")
    fmt = "{:<7} {:<7} {:<46} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4}  {}"
    columns = ("Req", "Risk", "Title", "Decl", "Pass", "Fail", "Dfct", "Blck", "Man", "Status")
    terminalreporter.write_line(fmt.format(*columns))
    for row in rows:
        terminalreporter.write_line(fmt.format(*(str(c)[:46] for c in row.cells())))

    out = Path(config.rootpath, "reports")
    out.mkdir(exist_ok=True)
    with (out / "traceability.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([HEADER, *(row.cells() for row in rows)])
    (out / "traceability.md").write_text(to_markdown(rows), encoding="utf-8")


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """Coverage gate (--fail-on-uncovered): every registered requirement needs a scenario.

    Computed here from the registry and the feature files, not from the
    terminal summary, because the summary is printed after this hook.
    """
    config = session.config
    if not config.getoption("fail_on_uncovered") or hasattr(config, "workerinput"):
        return
    declared = declared_scenarios(_features_dir(config))
    uncovered = [req for req in registry_of(config) if req not in declared]
    if uncovered:
        config.get_terminal_writer().line(f"Coverage gate failed - no scenarios for: {uncovered}", red=True)
        if session.exitstatus == pytest.ExitCode.OK:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
