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
from framework.perf.jtl import Sample, percentile, read_jtl, stats_by_label, timeline
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
