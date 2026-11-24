"""Performance quality gate: compare a JMeter run with the objectives in perf/sla.toml.

    python -m framework.perf.gate reports/perf/orders.jtl --profile sandbox --out reports/perf

Exit code 0 = every objective met; 1 = at least one missed (CI fails the stage); 2 = usage error.
A label with too few samples FAILS: a gate that passes on no evidence proves nothing (Unit 3, Day 12).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from framework.perf.jtl import (
    Bucket,
    Stats,
    Window,
    read_jtl,
    response_codes,
    stats_by_label,
    steady_state,
    timeline,
)


@dataclass(frozen=True)
class Objective:
    label: str
    min_samples: int
    max_error_pct: float
    p95_ms: float | None = None
    p99_ms: float | None = None
    min_throughput_per_s: float | None = None
    whole_run: bool = False  # True: judged on every sample (set-up and verification checks)


RESERVED = ("defaults", "steady_state")


@dataclass(frozen=True)
class SteadyState:
    skip_head_s: float
    skip_tail_s: float
    thread_prefix: str


def load_steady_state(path: Path, profile: str) -> SteadyState | None:
    """The profile's steady-state window from sla.toml ``[steady_state.<profile>]``, if any."""
    data = tomllib.loads(path.read_text(encoding="utf-8")).get("steady_state", {}).get(profile)
    if data is None:
        return None
    return SteadyState(
        float(data["skip_head_s"]), float(data["skip_tail_s"]), str(data.get("thread_prefix", ""))
    )


@dataclass(frozen=True)
class Verdict:
    label: str
    check: str
    expected: str
    actual: str
    passed: bool


def load_objectives(path: Path, profile: str) -> list[Objective]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    defaults: dict[str, Any] = data.get("defaults", {})
    if profile not in data or profile in RESERVED:
        raise KeyError(
            f"profile {profile!r} not in {path}; profiles: {sorted(k for k in data if k not in RESERVED)}"
        )
    objectives = []
    for label, values in data[profile].items():
        merged = {**defaults, **values}
        objectives.append(
            Objective(
                label=label,
                min_samples=int(merged.get("min_samples", 1)),
                max_error_pct=float(merged.get("max_error_pct", 0.0)),
                p95_ms=merged.get("p95_ms"),
                p99_ms=merged.get("p99_ms"),
                min_throughput_per_s=merged.get("min_throughput_per_s"),
                whole_run=merged.get("window") == "whole",
            )
        )
    return objectives


def evaluate(
    stats: Mapping[str, Stats],
    objectives: Sequence[Objective],
    whole_run: Mapping[str, Stats] | None = None,
) -> list[Verdict]:
    """Judge each objective on the steady-state ``stats`` (or on ``whole_run`` when it asks for it)."""
    verdicts: list[Verdict] = []
    for o in objectives:
        s = (whole_run if o.whole_run and whole_run is not None else stats).get(o.label)
        count = s.count if s else 0
        verdicts.append(
            Verdict(o.label, "samples", f">= {o.min_samples}", str(count), count >= o.min_samples)
        )
        if s is None:
            continue
        verdicts.append(
            Verdict(
                o.label,
                "errors %",
                f"<= {o.max_error_pct:g}",
                f"{s.error_pct:.2f}",
                s.error_pct <= o.max_error_pct,
            )
        )
        for name, limit, actual in (("p95 ms", o.p95_ms, s.p95_ms), ("p99 ms", o.p99_ms, s.p99_ms)):
            if limit is not None:
                verdicts.append(Verdict(o.label, name, f"<= {limit:g}", f"{actual:.0f}", actual <= limit))
        if o.min_throughput_per_s is not None:
            ok = not math.isnan(s.throughput_per_s) and s.throughput_per_s >= o.min_throughput_per_s
            verdicts.append(
                Verdict(
                    o.label,
                    "throughput /s",
                    f">= {o.min_throughput_per_s:g}",
                    f"{s.throughput_per_s:.2f}",
                    ok,
                )
            )
    return verdicts


@dataclass(frozen=True)
class Report:
    """Everything the gate writes: one object, so the Markdown and the JSON cannot disagree."""

    title: str
    stats: Mapping[str, Stats]
    verdicts: Sequence[Verdict]
    window: Window | None = None
    codes: Mapping[str, Mapping[str, int]] | None = None
    buckets: Sequence[Bucket] = ()
    notes: Sequence[str] = ()


def executive_summary(report: Report) -> list[str]:
    """Three lines for a manager: verdict, scope of the evidence, the worst miss (CT-PT 4.4.1)."""
    failed = [v for v in report.verdicts if not v.passed]
    total = sum(s.count for s in report.stats.values())
    errors = sum(s.errors for s in report.stats.values())
    lines = [
        (
            f"**Verdict: {'PASSED' if not failed else 'FAILED'}** - {len(report.verdicts) - len(failed)} of "
            f"{len(report.verdicts)} checks met."
        ),
        f"Evidence: {total} samples, {errors} errors"
        + (
            f"; steady state +{report.window.start_s:.0f} s to +{report.window.end_s:.0f} s "
            f"({report.window.kept} of {report.window.total} load samples)."
            if report.window
            else " (whole run: no steady-state window configured)."
        ),
    ]
    if failed:
        worst = failed[0]
        lines.append(
            f"First miss: {worst.label} - {worst.check} expected {worst.expected}, actual {worst.actual}."
        )
    return lines


def to_markdown(report: Report) -> str:
    lines = [f"# {report.title}", "", "## Executive summary", "", *executive_summary(report), ""]
    lines += [*(f"> {n}" for n in report.notes), ""] if report.notes else []
    lines += ["## Statistics" + (" (steady state)" if report.window else " (all labels)"), ""]
    lines += [
        "| Label | Samples | Errors % | Mean ms | p50 | p90 | p95 | p99 | Max | Throughput /s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in report.stats.values():
        cells = [s.label, str(s.count), f"{s.error_pct:.2f}"]
        cells += [f"{v:.0f}" for v in (s.mean_ms, s.p50_ms, s.p90_ms, s.p95_ms, s.p99_ms, s.max_ms)]
        lines.append("| " + " | ".join([*cells, f"{s.throughput_per_s:.2f}"]) + " |")
    failed = [v for v in report.verdicts if not v.passed]
    lines += ["", f"## Objectives: {'PASSED' if not failed else f'FAILED ({len(failed)})'}", ""]
    lines += ["| Label | Check | Expected | Actual | Result |", "|---|---|---|---|---|"]
    lines += [
        f"| {v.label} | {v.check} | {v.expected} | {v.actual} | {'pass' if v.passed else '**FAIL**'} |"
        for v in report.verdicts
    ]
    if report.codes:
        lines += ["", "## Response codes (whole run)", "", "| Label | Codes |", "|---|---|"]
        lines += [
            f"| {label} | {', '.join(f'{code}: {n}' for code, n in codes.items())} |"
            for label, codes in report.codes.items()
        ]
    if report.buckets:
        lines += [
            "",
            "## Load over time (whole run: ramp-up, steady state, ramp-down)",
            "",
            "| From s | Active threads | Samples | Errors | p95 ms |",
            "|---:|---:|---:|---:|---:|",
        ]
        lines += [
            f"| {b.start_s} | {b.threads} | {b.count} | {b.errors} | {b.p95_ms:.0f} |" for b in report.buckets
        ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.perf.gate", description=__doc__)
    parser.add_argument("jtl", type=Path)
    parser.add_argument("--sla", type=Path, default=Path("perf/sla.toml"))
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", type=Path, default=Path("reports/perf"))
    parser.add_argument("--skip-head", type=float, help="seconds of ramp-up to exclude (overrides sla.toml)")
    parser.add_argument(
        "--skip-tail", type=float, help="seconds of ramp-down to exclude (overrides sla.toml)"
    )
    parser.add_argument("--timeline-label", help="label whose load over time is reported")
    args = parser.parse_args(argv)
    try:
        objectives = load_objectives(args.sla, args.profile)
        steady = load_steady_state(args.sla, args.profile)
        samples = read_jtl(args.jtl)
    except (OSError, KeyError, ValueError) as error:
        print(f"perf gate: {error}", file=sys.stderr)
        return 2
    whole = stats_by_label(samples)
    window = None
    stats = whole
    if steady is not None or args.skip_head is not None or args.skip_tail is not None:
        steady = steady or SteadyState(0.0, 0.0, "")
        head = steady.skip_head_s if args.skip_head is None else args.skip_head
        tail = steady.skip_tail_s if args.skip_tail is None else args.skip_tail
        kept, window = steady_state(
            samples, skip_head_s=head, skip_tail_s=tail, thread_prefix=steady.thread_prefix
        )
        stats = stats_by_label(kept)
    verdicts = evaluate(stats, objectives, whole_run=whole)
    buckets = timeline(samples, args.timeline_label, bucket_s=10) if args.timeline_label else []
    report = Report(
        f"Performance gate - {args.profile}", stats, verdicts, window, response_codes(samples), buckets
    )
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"gate-{args.profile}"
    (args.out / f"{stem}.md").write_text(to_markdown(report), encoding="utf-8")
    (args.out / f"{stem}.json").write_text(
        json.dumps(
            {
                "window": asdict(window) if window else None,
                "stats": [asdict(s) for s in stats.values()],
                "verdicts": [asdict(v) for v in verdicts],
                "codes": report.codes,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    failed = [v for v in verdicts if not v.passed]
    for v in verdicts:
        print(
            f"{'PASS' if v.passed else 'FAIL'}  {v.label:<45} {v.check:<14} "
            f"expected {v.expected:<10} actual {v.actual}"
        )
    if window:
        print(
            f"steady state: +{window.start_s:.0f} s to +{window.end_s:.0f} s, "
            f"{window.kept}/{window.total} load samples"
        )
    print(
        f"perf gate {args.profile}: {'PASSED' if not failed else f'FAILED ({len(failed)} objective(s))'}"
        f" -> {args.out / (stem + '.md')}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
