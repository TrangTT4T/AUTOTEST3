"""Correlate load-test results with system telemetry to find the bottleneck (Unit 4, Day 16, LO8).

    python -m framework.perf.correlate reports/perf/orders.jtl reports/perf/telemetry.csv \
        --label "TX order completed" --out reports/perf/bottleneck.md

The same reasoning applies to CloudWatch: line up client-side response times and throughput with
server-side queue depth and consumer rates on one time axis, then look for the resource whose
queue grows while its processing rate stays flat.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from framework.perf.jtl import Sample, percentile, read_jtl

QUEUE_THRESHOLD = 2.0  # mean queued messages that marks a consumer as saturated


@dataclass(frozen=True)
class TelemetryRow:
    wall_ms: int
    subscription: str
    queued: int
    processed: int


def read_telemetry(path: Path) -> list[TelemetryRow]:
    with path.open(encoding="utf-8", newline="") as f:
        return [
            TelemetryRow(int(r["wall_ms"]), r["subscription"], int(r["queued"]), int(r["processed"]))
            for r in csv.DictReader(f)
        ]


@dataclass(frozen=True)
class Window:
    start_s: int
    users: int
    completed_per_s: float
    p95_ms: float
    errors: int
    queued: dict[str, float] = field(default_factory=dict)  # mean queue depth in the window
    processed_per_s: dict[str, float] = field(default_factory=dict)


def windows(
    samples: Sequence[Sample], label: str, telemetry: Sequence[TelemetryRow], bucket_s: int = 5
) -> list[Window]:
    if not samples:
        return []
    origin = min(s.start_ms for s in samples)
    end = max(s.end_ms for s in samples)
    by_bucket: dict[int, list[Sample]] = defaultdict(list)
    for s in samples:
        if s.label == label:
            by_bucket[(s.end_ms - origin) // 1000 // bucket_s].append(s)
    tele: dict[str, list[TelemetryRow]] = defaultdict(list)
    for row in sorted(telemetry, key=lambda r: r.wall_ms):
        tele[row.subscription].append(row)
    result = []
    for b in range((end - origin) // 1000 // bucket_s + 1):
        lo, hi = origin + b * bucket_s * 1000, origin + (b + 1) * bucket_s * 1000
        group = by_bucket.get(b, [])
        queued, rates = {}, {}
        for name, rows in tele.items():
            inside = [r for r in rows if lo <= r.wall_ms < hi]
            if inside:
                queued[name] = sum(r.queued for r in inside) / len(inside)
            before = [r for r in rows if r.wall_ms < lo][-1:] or inside[:1]
            if before and inside and inside[-1].wall_ms > before[0].wall_ms:
                rates[name] = (
                    (inside[-1].processed - before[0].processed)
                    * 1000
                    / (inside[-1].wall_ms - before[0].wall_ms)
                )
        result.append(
            Window(
                start_s=b * bucket_s,
                users=max((s.threads for s in group), default=0),
                completed_per_s=len(group) / bucket_s,
                p95_ms=percentile([s.elapsed_ms for s in group], 95),
                errors=sum(not s.success for s in group),
                queued=queued,
                processed_per_s=rates,
            )
        )
    return result


@dataclass(frozen=True)
class Diagnosis:
    bottleneck: str | None
    capacity_per_s: float | None
    evidence: list[str]


def diagnose(rows: Sequence[Window]) -> Diagnosis:
    """The consumer whose queue stays high at full load is the bottleneck; its rate is the capacity."""
    if not rows:
        return Diagnosis(None, None, ["no data"])
    peak = max(w.users for w in rows)
    steady = [w for w in rows if w.users == peak and w.queued]
    if not steady:
        return Diagnosis(None, None, ["no telemetry at full load"])
    names = sorted({n for w in steady for n in w.queued})
    mean_q = {n: sum(w.queued.get(n, 0.0) for w in steady) / len(steady) for n in names}
    mean_rate = {n: sum(w.processed_per_s.get(n, 0.0) for w in steady) / len(steady) for n in names}
    candidate = max(names, key=lambda n: mean_q[n])
    others = ", ".join(f"{n} {mean_q[n]:.1f}" for n in names if n != candidate)
    evidence = [
        (
            f"at full load ({peak} users, {len(steady)} windows): "
            f"mean queue {candidate} {mean_q[candidate]:.1f}; {others}"
        ),
        "processing rates: " + ", ".join(f"{n} {mean_rate[n]:.1f}/s" for n in names),
    ]
    completed = sum(w.completed_per_s for w in steady) / len(steady)
    p95 = sum(w.p95_ms for w in steady) / len(steady)
    evidence.append(f"client side: {completed:.1f} completed/s, p95 {p95:.0f} ms")
    if mean_q[candidate] < QUEUE_THRESHOLD:
        evidence.append("no queue builds up: the system is not saturated at this load")
        return Diagnosis(None, None, evidence)
    return Diagnosis(candidate, mean_rate[candidate], evidence)


def to_markdown(rows: Sequence[Window], diagnosis: Diagnosis, label: str) -> str:
    names = sorted({n for w in rows for n in w.queued})
    header = ["Window (s)", "Users", f"{label} /s", "p95 ms", "Errors"]
    header += [f"{n} queued" for n in names] + [f"{n} /s" for n in names]
    lines = ["# Load vs telemetry", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for w in rows:
        cells = [f"{w.start_s}", str(w.users), f"{w.completed_per_s:.1f}", f"{w.p95_ms:.0f}", str(w.errors)]
        cells += [f"{w.queued.get(n, 0):.1f}" for n in names] + [
            f"{w.processed_per_s.get(n, 0):.1f}" for n in names
        ]
        lines.append("| " + " | ".join(cells) + " |")
    verdict = (
        f"**Bottleneck: `{diagnosis.bottleneck}`**, capacity about {diagnosis.capacity_per_s:.1f}/s"
        if diagnosis.bottleneck
        else "**No bottleneck at this load**"
    )
    lines += ["", "## Diagnosis", "", verdict, "", *(f"- {e}" for e in diagnosis.evidence)]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.perf.correlate", description=__doc__)
    parser.add_argument("jtl", type=Path)
    parser.add_argument("telemetry", type=Path)
    parser.add_argument("--label", default="TX order completed")
    parser.add_argument("--bucket", type=int, default=5)
    parser.add_argument("--out", type=Path, default=Path("reports/perf/bottleneck.md"))
    args = parser.parse_args(argv)
    rows = windows(read_jtl(args.jtl), args.label, read_telemetry(args.telemetry), args.bucket)
    diagnosis = diagnose(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_markdown(rows, diagnosis, args.label), encoding="utf-8")
    print(
        f"bottleneck: {diagnosis.bottleneck or 'none'}; " + "; ".join(diagnosis.evidence) + f" -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
