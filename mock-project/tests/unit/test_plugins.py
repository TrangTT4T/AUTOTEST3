"""The pytest plugins, run end to end on a tiny project in a sandbox (pytester).

These tests use no browser: the steps are plain functions, and pytest-playwright is switched
off inside the sandbox (its per-test assertion scope cannot nest inside the outer run's).
They prove the rules the whole suite relies on: a finding turns into a STRICT xfail for its
persona only, a fixed defect turns the run red, a different kind of failure is never hidden,
and the gates really gate.
"""

import json

import pytest

pytest_plugins = ["pytester"]

INI = """
[pytest]
bdd_features_base_dir = features
requirements_registry = requirements.toml
findings_register = findings.toml
perf_budgets = perf-budgets.toml
addopts = -p no:cacheprovider -p no:playwright
markers =
    smoke: s
    regression: r
    manual: m
    persona-independent: p
    known_defect(id): k
    risk-high: h
    risk-low: l
"""

REQUIREMENTS = """
[REQ-1]
title = "Sorting"
risk = "high"

[REQ-2]
title = "Something else"
risk = "low"
"""

FINDINGS = """
[areas]
sorting = "sorting works"

[SL-01]
title = "Sorting is broken"
personas = ["problem_user"]
area = "sorting"
requirement = "REQ-1"
severity = "major"
"""

FEATURE = """
Feature: Sandbox
  @smoke @risk-high @REQ-1 @area-sorting
  Scenario: Sorting
    Given a shop
    Then sorting works

  @regression @risk-low @REQ-2 @persona-independent
  Scenario: Independent
    Given a shop
    Then it works

  @manual @REQ-2
  Scenario: By hand
    Given a shop
"""

STEPS = """
from pytest_bdd import given, scenarios, then

scenarios(".")

@given("a shop")
def a_shop():
    pass

@then("sorting works")
def sorting_works():
    {sorting}

@then("it works")
def it_works():
    pass
"""

CONFTEST = """
pytest_plugins = ["swaglabs.plugins.registry", "swaglabs.plugins.findings", "swaglabs.plugins.reporting"]
"""


@pytest.fixture
def project(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    monkeypatch.setenv("SWAGLABS_BASE_URL", "https://shop.invalid")  # no pytest-playwright here
    pytester.makeini(INI)
    pytester.makeconftest(CONFTEST)
    (pytester.path / "requirements.toml").write_text(REQUIREMENTS, encoding="utf-8")
    (pytester.path / "findings.toml").write_text(FINDINGS, encoding="utf-8")
    (pytester.path / "perf-budgets.toml").write_text("[budgets]\nsort = 2000\n", encoding="utf-8")
    (pytester.path / "features").mkdir()
    (pytester.path / "features" / "sandbox.feature").write_text(FEATURE, encoding="utf-8")
    write_steps(pytester, "assert False, 'the order did not change'")
    return pytester


def write_steps(pytester: pytest.Pytester, sorting: str) -> None:
    (pytester.path / "test_scenarios.py").write_text(STEPS.format(sorting=sorting), encoding="utf-8")


def traceability(pytester: pytest.Pytester) -> dict[str, str]:
    data = json.loads((pytester.path / "reports" / "traceability.json").read_text(encoding="utf-8"))
    return {row["id"]: row["status"] for row in data["rows"]}


def test_a_finding_becomes_a_strict_xfail_for_its_persona(project: pytest.Pytester) -> None:
    result = project.runpytest("--persona", "problem_user")
    result.assert_outcomes(xfailed=1, skipped=1, deselected=1)
    assert traceability(project) == {"REQ-1": "KNOWN DEFECT", "REQ-2": "MANUAL"}
    reports = project.path / "reports"
    assert {"run.json", "manifest.json", "perf.md", "traceability.md"} <= {p.name for p in reports.iterdir()}
    run = json.loads((reports / "run.json").read_text(encoding="utf-8"))
    assert run["outcomes"] == {"known-defect": 1, "skipped": 1}
    assert run["settings"]["persona"] == "problem_user"
    assert "SL-01" in json.loads((reports / "traceability.json").read_text(encoding="utf-8"))["known_defects"]


def test_other_personas_see_the_failure_as_a_failure(project: pytest.Pytester) -> None:
    result = project.runpytest("--persona", "standard_user")
    result.assert_outcomes(failed=1, passed=1, skipped=1)
    assert traceability(project)["REQ-1"] == "FAIL"


def test_a_fixed_defect_turns_the_run_red(project: pytest.Pytester) -> None:
    write_steps(project, "pass")
    result = project.runpytest("--persona", "problem_user")
    result.assert_outcomes(failed=1, skipped=1, deselected=1)
    result.stdout.fnmatch_lines(["*XPASS(strict)*SL-01*"])


def test_a_different_kind_of_failure_is_never_hidden(project: pytest.Pytester) -> None:
    write_steps(project, "raise RuntimeError('our own bug')")
    result = project.runpytest("--persona", "problem_user")
    result.assert_outcomes(failed=1, skipped=1, deselected=1)


def test_coverage_gate_fails_on_an_uncovered_requirement(project: pytest.Pytester) -> None:
    registry = project.path / "requirements.toml"
    extra = '\n[REQ-3]\ntitle = "Nobody tests me"\nrisk = "low"\n'
    registry.write_text(REQUIREMENTS + extra, encoding="utf-8")
    result = project.runpytest("--collect-only", "-q", "--fail-on-uncovered")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*Coverage gate: requirement REQ-3 has no scenario*"])


def test_coverage_gate_fails_on_an_undetectable_finding(project: pytest.Pytester) -> None:
    feature = project.path / "features" / "sandbox.feature"
    feature.write_text(FEATURE.replace(" @area-sorting", ""), encoding="utf-8")
    result = project.runpytest("--collect-only", "-q", "--fail-on-uncovered")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*finding SL-01 has no scenario with its area*"])


def test_broken_tags_stop_the_run_before_anything_executes(project: pytest.Pytester) -> None:
    feature = project.path / "features" / "sandbox.feature"
    feature.write_text(FEATURE.replace("@risk-high @REQ-1", "@risk-low @REQ-1"), encoding="utf-8")
    result = project.runpytest()
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*Tag rules broken*", "*@risk-low but the registry says high*"])
