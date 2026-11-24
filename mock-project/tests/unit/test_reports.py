"""Traceability, the persona matrix, timings and evidence files."""

import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from swaglabs import matrix
from swaglabs.evidence import (
    JsonLineFormatter,
    RedactingFilter,
    build_manifest,
    redact,
    run_record,
    slug,
    verify_manifest,
    write_manifest,
)
from swaglabs.evidence import main as evidence_main
from swaglabs.perf import (
    Measurement,
    busy_time,
    load_budgets,
    percentile,
    summarise,
    to_markdown,
    window_activity,
)
from swaglabs.requirements import Requirement
from swaglabs.traceability import build_matrix, declared_scenarios, status_of
from swaglabs.traceability import to_markdown as trace_markdown

REGISTRY = {
    "REQ-1": Requirement("REQ-1", "one", "high"),
    "REQ-2": Requirement("REQ-2", "two", "low"),
    "REQ-3": Requirement("REQ-3", "three", "low"),
}


class TestTraceability:
    @pytest.mark.parametrize(
        ("outcomes", "status"),
        [
            ({"passed": 3, "failed": 1}, "FAIL"),
            ({"passed": 3, "known-defect": 1}, "KNOWN DEFECT"),
            ({"passed": 1, "skipped": 1}, "PASS"),
            ({"skipped": 1}, "MANUAL"),
            ({}, "NOT RUN"),
        ],
    )
    def test_worst_outcome_decides(self, outcomes: dict[str, int], status: str) -> None:
        assert status_of(1, outcomes) == status

    def test_uncovered_beats_everything(self) -> None:
        assert status_of(0, {"passed": 5}) == "NOT COVERED"

    def test_matrix_and_markdown(self) -> None:
        declared = {"REQ-1": ["a"], "REQ-2": ["b"]}
        rows = build_matrix(REGISTRY, declared, [(["REQ-1"], "passed"), (["REQ-1", "REQ-2"], "known-defect")])
        assert [r.status for r in rows] == ["KNOWN DEFECT", "KNOWN DEFECT", "NOT COVERED"]
        text = trace_markdown(rows, "T")
        assert "| REQ-3 | low | three | 0 | 0 | 0 | 0 | 0 | **NOT COVERED** |" in text
        assert rows[0].as_dict()["outcomes"]["passed"] == 1

    def test_declared_scenarios_merge_feature_rule_and_examples_tags(self, tmp_path: Path) -> None:
        (tmp_path / "x.feature").write_text(
            """@REQ-1
Feature: F
  Rule: R
    @smoke
    Scenario Outline: S
      Given <a>

      @area-y
      Examples:
        | a |
        | 1 |
""",
            encoding="utf-8",
        )
        [scenario] = declared_scenarios(tmp_path)
        assert scenario.requirements == ["REQ-1"]
        assert scenario.areas == ["y"]
        assert "smoke" in scenario.tags


def _run(label: str, statuses: dict[str, str], defects: list[str]) -> dict[str, object]:
    return {
        "label": label,
        "known_defects": defects,
        "rows": [{"id": k, "title": k.lower(), "status": v} for k, v in statuses.items()],
    }


class TestMatrix:
    def test_merges_runs_side_by_side(self) -> None:
        text = matrix.merge(
            [
                _run("b-run", {"REQ-1": "PASS", "REQ-2": "KNOWN DEFECT"}, ["SL-02"]),
                _run("a-run", {"REQ-1": "PASS"}, []),
            ]
        )
        assert "| Requirement | b-run | a-run |" in text
        assert "| REQ-2 req-2 | DEFECT | - |" in text
        assert "Known defects observed: SL-02." in text
        assert "Runs with unexpected failures: none." in text

    def test_needs_at_least_one_run(self) -> None:
        with pytest.raises(ValueError, match="no traceability"):
            matrix.merge([])

    def test_cli_exit_code_gates_on_failures(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        good, bad = tmp_path / "good.json", tmp_path / "bad.json"
        good.write_text(json.dumps(_run("good", {"REQ-1": "PASS"}, [])), encoding="utf-8")
        bad.write_text(json.dumps(_run("bad", {"REQ-1": "FAIL"}, [])), encoding="utf-8")
        assert matrix.main([str(good)]) == 0
        assert matrix.main([str(good), str(bad)]) == 1
        assert "Runs with unexpected failures: bad." in capsys.readouterr().out


class TestPerf:
    def test_busy_time_counts_overlaps_once_and_clips(self) -> None:
        assert busy_time([(0, 1), (0.5, 2), (3, 4)], 0, 10) == 3
        assert busy_time([(-5, 1), (9, 20)], 0, 10) == 2
        assert busy_time([(11, 12)], 0, 10) == 0
        assert busy_time([], 0, 10) == 0

    def test_window_activity_ignores_old_unfinished_requests(self) -> None:
        finished = [(0.0, 1.0), (4.0, 6.0), (9.0, 9.5)]
        intervals, started = window_activity(finished, in_flight_starts=[1.0, 7.0], start=5.0, end=10.0)
        # (4, 6) overlaps; (9, 9.5) is inside; the request open since 1.0 is NOT counted; the one
        # opened at 7.0 is busy until the end of the window.
        assert sorted(intervals) == [(4.0, 6.0), (7.0, 10.0), (9.0, 9.5)]
        assert started == 2
        assert busy_time(intervals, 5.0, 10.0) == 4.0

    @pytest.mark.parametrize(
        ("duration", "network", "bottleneck"),
        [(5000, 100, "client"), (1000, 900, "network"), (1000, 500, "mixed"), (0, 0, "client")],
    )
    def test_bottleneck(self, duration: float, network: float, bottleneck: str) -> None:
        assert Measurement("x", duration, network, 1).bottleneck == bottleneck

    def test_percentile_nearest_rank(self) -> None:
        values = list(range(1, 21))
        assert percentile(values, 95) == 19
        assert percentile(values, 50) == 10
        assert percentile([7], 99) == 7
        with pytest.raises(ValueError, match="no values"):
            percentile([], 50)
        with pytest.raises(ValueError, match="percentile"):
            percentile([1], 0)

    def test_summary_and_report(self) -> None:
        ms = [
            Measurement("login", 5100, 300, 4),
            Measurement("login", 180, 120, 4),
            Measurement("x", 10, 0, 0),
        ]
        stats = summarise(ms, {"login": 2500})
        login = next(s for s in stats if s.action == "login")
        assert (login.samples, login.max_ms) == (2, 5100)
        assert (login.within_budget, login.bottleneck) == (False, "client")
        assert next(s for s in stats if s.action == "x").within_budget is None
        text = to_markdown(stats, "glitch")
        assert "| login | 2 | 180 | 5100 | 5100 | 2500 | OVER BUDGET | client |" in text
        assert "| x | 1 | 10 | 10 | 10 | - | no budget | client |" in text

    def test_measurement_round_trip(self) -> None:
        m = Measurement("sort", 120.5, 60.0, 3, "t::1")
        data = m.as_dict()
        assert data["client_ms"] == 60.5
        assert Measurement.from_dict(data) == m

    def test_budget_file(self, tmp_path: Path) -> None:
        path = tmp_path / "b.toml"
        path.write_text("[budgets]\nlogin = 2500\n", encoding="utf-8")
        assert load_budgets(path) == {"login": 2500.0}
        path.write_text("[budgets]\nlogin = 0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="positive"):
            load_budgets(path)


class TestEvidence:
    def test_slug(self) -> None:
        assert slug("test_a[Ada-Lovelace-/x y]") == "test_a_Ada-Lovelace-_x_y"
        assert slug("///") == "unnamed"

    def test_redact_longest_first_and_ignores_empty(self) -> None:
        assert redact("pw=secret_sauce s=secret", ["secret", "secret_sauce", ""]) == "pw=*** s=***"

    def test_json_formatter_masks_secrets(self) -> None:
        record = logging.LogRecord("swaglabs", logging.INFO, __file__, 1, "typed %s", ("hunter2",), None)
        line = json.loads(JsonLineFormatter(secrets=["hunter2"], static={"worker": "gw0"}).format(record))
        assert line["message"] == "typed ***"
        assert line["worker"] == "gw0"
        assert line["ts"].endswith("+00:00")

    def test_json_formatter_includes_exceptions(self) -> None:
        def fail() -> None:
            raise RuntimeError("boom hunter2")

        try:
            fail()
        except RuntimeError:
            record = logging.LogRecord("swaglabs", logging.ERROR, __file__, 1, "failed", None, sys.exc_info())
        line = json.loads(JsonLineFormatter(secrets=["hunter2"]).format(record))
        assert "boom ***" in line["exception"]

    def test_redacting_filter_rewrites_the_record(self) -> None:
        record = logging.LogRecord("swaglabs", logging.INFO, __file__, 1, "pw %s", ("hunter2",), None)
        assert RedactingFilter(["hunter2"]).filter(record)
        assert record.getMessage() == "pw ***"
        clean = logging.LogRecord("swaglabs", logging.INFO, __file__, 1, "nothing %s", ("here",), None)
        RedactingFilter(["hunter2"]).filter(clean)
        assert clean.args == ("here",)

    def test_manifest_detects_changes(self, tmp_path: Path) -> None:
        (tmp_path / "evidence").mkdir()
        (tmp_path / "run.json").write_text("{}", encoding="utf-8")
        (tmp_path / "evidence" / "shot.png").write_bytes(b"\x89PNG")
        write_manifest(tmp_path)
        assert verify_manifest(tmp_path) == []
        assert set(build_manifest(tmp_path)["files"]) == {"run.json", "evidence/shot.png"}
        (tmp_path / "run.json").write_text('{"edited": true}', encoding="utf-8")
        (tmp_path / "extra.txt").write_text("x", encoding="utf-8")
        (tmp_path / "evidence" / "shot.png").unlink()
        assert verify_manifest(tmp_path) == [
            "missing: evidence/shot.png",
            "changed: run.json",
            "not in manifest: extra.txt",
        ]

    def test_command_line_verification(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "run.json").write_text("{}", encoding="utf-8")
        write_manifest(tmp_path)
        assert evidence_main([str(tmp_path)]) == 0
        (tmp_path / "run.json").write_text("[]", encoding="utf-8")
        assert evidence_main([str(tmp_path)]) == 1
        assert evidence_main([]) == 2
        captured = capsys.readouterr()
        assert "evidence intact" in captured.out
        assert "changed: run.json" in captured.err

    def test_run_record(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        record = run_record(
            settings={"persona": "p"},
            outcomes={"passed": 2, "failed": 1},
            started=start,
            finished=start + timedelta(seconds=90),
            environment={"GITHUB_SHA": "abc"},
        )
        assert record["duration_s"] == 90.0
        assert list(record["outcomes"]) == ["failed", "passed"]
