"""reports/ holds exactly one run's evidence (framework/plugins/evidence.py, a global setup)."""

from pathlib import Path

import pytest

from framework.plugins.evidence import reset_run_outputs

pytest_plugins = ["pytester"]


def test_reset_removes_only_this_suites_outputs_and_is_idempotent(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    (reports / "evidence" / "an_old_failure").mkdir(parents=True)
    (reports / "events").mkdir()
    (reports / "events" / "sandbox-gw7.log").write_text("old", encoding="utf-8")
    (reports / "traceability.md").write_text("old", encoding="utf-8")
    (reports / "perf").mkdir()  # JMeter's results: another tool's output
    (reports / "coverage.xml").write_text("<coverage/>", encoding="utf-8")

    assert sorted(reset_run_outputs(reports)) == ["events", "evidence", "traceability.md"]
    assert reset_run_outputs(reports) == []  # idempotent
    assert sorted(p.name for p in reports.iterdir()) == ["coverage.xml", "perf"]


def test_reset_never_follows_a_link(tmp_path: Path) -> None:
    keep = tmp_path / "keep"
    keep.mkdir()
    (keep / "precious.txt").write_text("x", encoding="utf-8")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "evidence").symlink_to(keep, target_is_directory=True)

    assert reset_run_outputs(tmp_path / "reports") == ["evidence"]
    assert (keep / "precious.txt").is_file()


def test_reset_tolerates_a_missing_reports_folder(tmp_path: Path) -> None:
    assert reset_run_outputs(tmp_path / "reports") == []


def test_the_controller_resets_before_the_run(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\naddopts = -p no:cacheprovider -p no:playwright\n")
    pytester.makeconftest('pytest_plugins = ["framework.plugins.evidence"]\n')
    stale = pytester.path / "reports" / "evidence" / "an_old_failure"
    stale.mkdir(parents=True)
    pytester.makepyfile("def test_ok():\n    pass\n")

    pytester.runpytest("--collect-only").assert_outcomes()
    assert stale.exists()  # collecting is not a run: nothing is deleted
    pytester.runpytest().assert_outcomes(passed=1)
    assert not stale.exists()
