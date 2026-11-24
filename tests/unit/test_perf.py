"""Unit tests for the performance tooling (framework/perf): no JMeter or sandbox needed."""

import csv
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from framework.perf.correlate import TelemetryRow, Window, diagnose, windows
from framework.perf.correlate import main as correlate_main
from framework.perf.gate import Objective, evaluate, load_objectives, main
from framework.perf.jtl import (
    Sample,
    percentile,
    read_jtl,
    response_codes,
    stats_by_label,
    steady_state,
    timeline,
)
from framework.perf.jtl import Window as SteadyWindow
from framework.perf.model import concurrency, jmeter_properties, load_workload, throughput
from framework.perf.model import main as model_main
from framework.perf.telemetry import FIELDS, rows_from
from framework.perf.telemetry import main as telemetry_main

ROOT = Path(__file__).resolve().parents[2]
HEADER = (
    "timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,"
    "bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n"
)


def _jtl(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "r.jtl"
    path.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def _sample(start: int, elapsed: int, label: str = "A", ok: bool = True, threads: int = 1) -> Sample:
    return Sample(start, elapsed, label, ok, "200" if ok else "500", "", threads)


def test_percentile_is_nearest_rank() -> None:
    values = list(range(1, 101))  # 1..100
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95
    assert percentile(values, 100) == 100
    assert percentile([7], 99) == 7


def test_jtl_with_commas_in_messages_is_parsed(tmp_path: Path) -> None:
    path = _jtl(
        tmp_path,
        [
            (
                '1000,120,TX order completed,200,"Number of samples in transaction : 7, '
                'number of failing samples : 0",'
                "Customers 1-1,,true,,1,1,1,1,null,0,0,0"
            ),
            "1100,30,POST /orders,500,Server Error,Customers 1-1,text,false,boom,1,1,1,1,http://x,0,0,0",
        ],
    )
    samples = read_jtl(path)
    assert [s.label for s in samples] == ["TX order completed", "POST /orders"]
    assert samples[1].success is False


def test_stats_error_rate_and_throughput() -> None:
    samples = [_sample(1000 * i, 100) for i in range(10)] + [_sample(500, 900, ok=False)]
    stats = stats_by_label(samples)["A"]
    assert stats.count == 11
    assert stats.errors == 1
    assert stats.error_pct == pytest.approx(100 / 11)
    assert stats.p95_ms == 900
    assert stats.throughput_per_s == pytest.approx(11 / 9.1)


def test_timeline_buckets_by_end_time() -> None:
    samples = [_sample(0, 100), _sample(4000, 2000), _sample(5000, 100, threads=3)]
    buckets = timeline(samples, "A", bucket_s=5)
    assert [(b.start_s, b.count, b.threads) for b in buckets] == [(0, 1, 1), (5, 2, 3)]


def test_gate_fails_on_too_few_samples_and_on_missing_labels() -> None:
    stats = stats_by_label([_sample(i * 10, 50) for i in range(5)])
    verdicts = evaluate(
        stats,
        [Objective("A", min_samples=20, max_error_pct=1.0, p95_ms=100), Objective("B", 1, 0.0)],
    )
    failed = {(v.label, v.check) for v in verdicts if not v.passed}
    assert failed == {("A", "samples"), ("B", "samples")}


def test_gate_checks_percentiles_not_averages() -> None:
    # Average 280 ms looks fine; p95 2000 ms does not (the Day 18 exam case in miniature).
    samples = [_sample(i * 10, 100) for i in range(90)] + [_sample(i * 10, 2000) for i in range(10)]
    stats = stats_by_label(samples)
    assert stats["A"].mean_ms == pytest.approx(290)
    verdicts = evaluate(stats, [Objective("A", 20, 1.0, p95_ms=1000)])
    assert [(v.check, v.passed) for v in verdicts if v.check == "p95 ms"] == [("p95 ms", False)]


def test_repository_sla_profiles_load() -> None:
    sandbox = load_objectives(ROOT / "perf/sla.toml", "sandbox")
    assert {o.label for o in sandbox} == {"POST /orders", "TX order completed"}
    assert next(o for o in sandbox if o.label == "TX order completed").p95_ms == 2000
    with pytest.raises(KeyError, match="profiles"):
        load_objectives(ROOT / "perf/sla.toml", "nope")


def test_gate_cli_exit_codes(tmp_path: Path) -> None:
    rows = [f"{1000 + i * 10},50,POST /orders,202,Accepted,t,text,true,,1,1,1,1,u,0,0,0" for i in range(30)]
    rows += [f"{1000 + i * 10},900,TX order completed,200,ok,t,,true,,1,1,1,1,null,0,0,0" for i in range(30)]
    jtl = _jtl(tmp_path, rows)
    assert (
        main([str(jtl), "--sla", str(ROOT / "perf/sla.toml"), "--profile", "sandbox", "--out", str(tmp_path)])
        == 0
    )
    assert (tmp_path / "gate-sandbox.md").read_text(encoding="utf-8").count("pass") >= 4
    assert main([str(jtl), "--sla", str(ROOT / "perf/sla.toml"), "--profile", "missing"]) == 2


def test_correlation_finds_the_saturated_consumer() -> None:
    steady = [
        Window(
            s, 40, 9.8, 4100, 0, {"fulfilment": 38.0, "payments": 0.1}, {"fulfilment": 9.8, "payments": 10.0}
        )
        for s in (10, 15, 20)
    ]
    ramp = Window(
        0, 20, 8.6, 1400, 0, {"fulfilment": 8.0, "payments": 0.0}, {"fulfilment": 8.0, "payments": 11.0}
    )
    diagnosis = diagnose([ramp, *steady])
    assert diagnosis.bottleneck == "fulfilment"
    assert diagnosis.capacity_per_s == pytest.approx(9.8)


def test_no_bottleneck_without_a_queue() -> None:
    calm = [Window(s, 5, 5.0, 300, 0, {"payments": 0.2}, {"payments": 5.0}) for s in (0, 5)]
    assert diagnose(calm).bottleneck is None


def test_windows_align_telemetry_with_samples() -> None:
    samples = [_sample(0, 1000, "TX", threads=2), _sample(5000, 1000, "TX", threads=2)]
    telemetry = [
        TelemetryRow(0, "payments", 4, 0),
        TelemetryRow(4000, "payments", 6, 20),
        TelemetryRow(6000, "payments", 2, 30),
    ]
    rows = windows(samples, "TX", telemetry, bucket_s=5)
    assert rows[0].queued["payments"] == 5.0
    assert rows[0].processed_per_s["payments"] == pytest.approx(5.0)
    assert rows[1].completed_per_s == pytest.approx(0.2)


# --- telemetry sampler and correlation CLI ------------------------------------------------------
class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(
            {
                "subscriptions": {
                    "payments": {
                        "queued": 3,
                        "in_flight": 1,
                        "processed": 10,
                        "failed": 0,
                        "held": 0,
                        "workers": 1,
                    }
                }
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # keep test output clean
        pass


def test_telemetry_rows_and_sampler(tmp_path: Path) -> None:
    assert rows_from(
        {"subscriptions": {"b": dict.fromkeys(FIELDS[2:], 1), "a": dict.fromkeys(FIELDS[2:], 2)}}, 7
    ) == [
        {
            "wall_ms": 7,
            "subscription": "a",
            "queued": 2,
            "in_flight": 2,
            "processed": 2,
            "failed": 2,
            "workers": 2,
        },
        {
            "wall_ms": 7,
            "subscription": "b",
            "queued": 1,
            "in_flight": 1,
            "processed": 1,
            "failed": 1,
            "workers": 1,
        },
    ]
    server = HTTPServer(("127.0.0.1", 0), _MetricsHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        out = tmp_path / "telemetry.csv"
        url = f"http://127.0.0.1:{server.server_port}"
        assert telemetry_main([url, "--out", str(out), "--duration", "0.25", "--interval", "0.1"]) == 0
    finally:
        server.shutdown()
        server.server_close()
    with out.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 2
    assert {r["subscription"] for r in rows} == {"payments"}
    assert rows[0]["queued"] == "3"


def test_correlate_cli_writes_the_report(tmp_path: Path) -> None:
    jtl = _jtl(tmp_path, [f"{1000 + i * 500},800,TX,200,ok,t,,true,,1,1,4,4,null,0,0,0" for i in range(20)])
    tele = tmp_path / "t.csv"
    tele.write_text(
        "wall_ms,subscription,queued,in_flight,processed,failed,workers\n"
        + "".join(f"{1000 + i * 1000},payments,{8 + i % 2},1,{i * 2},0,1\n" for i in range(12)),
        encoding="utf-8",
    )
    out = tmp_path / "bottleneck.md"
    assert correlate_main([str(jtl), str(tele), "--label", "TX", "--out", str(out)]) == 0
    report = out.read_text(encoding="utf-8")
    assert "**Bottleneck: `payments`**" in report


# --- Load profile, steady state and reporting (ISTQB CT-PT chapter 4) ------------------------------


def test_interactive_response_time_law() -> None:
    # The CT-PT example: 500 users, one query a minute vs one query an hour -> 60 x the load.
    per_minute = throughput(users=500, response_s=0, think_s=60)
    per_hour = throughput(users=500, response_s=0, think_s=3600)
    assert per_minute * 3600 == pytest.approx(30_000)
    assert per_hour * 3600 == pytest.approx(500)
    assert concurrency(rate_per_s=2.8, response_s=0.05, think_s=2.0) == pytest.approx(5.74)
    with pytest.raises(ValueError, match="response"):
        throughput(10, 0, 0)
    with pytest.raises(ValueError, match="must be >= 0"):
        concurrency(-1, 1, 1)


def test_repository_workload_derives_the_load_profile(capsys: pytest.CaptureFixture[str]) -> None:
    workload = load_workload(ROOT / "perf/workload.toml")
    rows = {r.journey.key: r for r in workload.rows()}
    assert rows["J1"].rate_per_s == pytest.approx(1.2)
    assert rows["J2"].users == pytest.approx(5.74)
    assert workload.load.journeys_started() == pytest.approx(320)
    assert jmeter_properties(workload) == {
        "rate": "4",
        "rampup": "20",
        "steady": "60",
        "rampdown": "20",
        "order_pct": "30",
    }
    assert model_main([str(ROOT / "perf/workload.toml")]) == 0
    out = capsys.readouterr().out
    assert "| **Total** | 100% | 4.00 | | | **6.9**" in out
    assert "-Jrate=4 -Jrampup=20 -Jsteady=60 -Jrampdown=20 -Jorder_pct=30" in out


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("share = 0.70", "share = 0.60"), "add up to 1.0"),
        (("peak_journeys_per_s = 4.0", "peak_journeys_per_s = 0"), "must be positive"),
        (
            (
                '[operational_profile.journeys.J1]\nname = "J1',
                '[operational_profile.journeys.J9]\nname = "J9',
            ),
            "needs journey J1",
        ),
    ],
)
def test_broken_workloads_are_refused(tmp_path: Path, change: tuple[str, str], message: str) -> None:
    text = (ROOT / "perf/workload.toml").read_text(encoding="utf-8").replace(*change)
    path = tmp_path / "w.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        jmeter_properties(load_workload(path))
    assert model_main([str(tmp_path / "missing.toml")]) == 2


def _load(start: int, elapsed: int, label: str = "A", thread: str = "Shoppers 1-1") -> Sample:
    return Sample(start, elapsed, label, success=True, code="200", message="", threads=1, thread=thread)


def test_steady_state_drops_ramps_and_non_load_threads() -> None:
    samples = [_load(t * 1000, 100) for t in range(0, 100, 5)]  # load from 0 s to 95.1 s
    samples += [
        _load(0, 50, "prepare", thread="Prepare 1-1"),
        _load(99_000, 50, "verify", thread="Verify 1-1"),
    ]
    kept, window = steady_state(samples, skip_head_s=20, skip_tail_s=20, thread_prefix="Shoppers")
    assert [s.start_ms // 1000 for s in kept] == list(range(20, 80, 5))  # the 75 s sample ends at 75.1 s
    assert (window.start_s, window.end_s, window.kept, window.total) == (20, 75.1, 12, 20)
    empty = steady_state(samples, skip_head_s=0, skip_tail_s=0, thread_prefix="Nobody")
    assert empty == ([], SteadyWindow(0, 0, 0, 0))


def test_response_codes_per_label() -> None:
    samples = [_sample(0, 1), _sample(1, 1, ok=False), _sample(2, 1, label="B")]
    assert response_codes(samples) == {"A": {"200": 1, "500": 1}, "B": {"200": 1}}


def test_whole_run_objectives_use_every_sample() -> None:
    steady = stats_by_label([_sample(i, 1) for i in range(30)])
    whole = stats_by_label([_sample(0, 1, label="prepare")])
    objectives = [Objective("A", 20, 0.0), Objective("prepare", 1, 0.0, whole_run=True)]
    assert all(v.passed for v in evaluate(steady, objectives, whole_run=whole))
    assert not all(v.passed for v in evaluate(steady, objectives))  # without the whole run it is missing


def test_profile_gate_end_to_end(tmp_path: Path) -> None:
    def row(t_ms: int, ms: int, label: str, thread: str, ok: str = "true") -> str:
        return f"{t_ms},{ms},{label},200,OK,{thread},text,{ok},,1,1,5,5,u,0,0,0"

    rows = [row(s * 200, 300, "J1 Place order and track", "Shoppers 1-1") for s in range(500)]  # 0-100 s, 5/s
    rows += [row(s * 100, 2, "J1.1 Submit order", "Shoppers 1-2") for s in range(1000)]
    rows += [row(s * 100 + 50, 2, "J2 Check order status", "Shoppers 1-3") for s in range(1000)]
    rows += [row(0, 5, "prepare: test data ready", "Prepare 1-1")]
    rows += [row(100_500, 5, "verify: GET /metrics", "Verify 1-1")]
    rows += [row(100_600, 5, "verify: run completed without abort", "Verify 1-1", ok="false")]
    jtl = _jtl(tmp_path, rows)
    args = [
        str(jtl),
        "--sla",
        str(ROOT / "perf/sla.toml"),
        "--profile",
        "sandbox_profile",
        "--out",
        str(tmp_path),
    ]
    assert main([*args, "--timeline-label", "J2 Check order status"]) == 1  # the abort check failed
    report = (tmp_path / "gate-sandbox_profile.md").read_text(encoding="utf-8")
    assert "**Verdict: FAILED** - 16 of 17 checks met." in report
    assert "steady state +20 s to +80 s" in report
    assert "First miss: verify: run completed without abort - errors %" in report
    assert "## Load over time" in report
    assert "| J2 Check order status | 200: 1000 |" in report
    assert main([*args, "--skip-head", "0", "--skip-tail", "0"]) == 1
    assert "steady state +0 s to +100 s" in (tmp_path / "gate-sandbox_profile.md").read_text(encoding="utf-8")
