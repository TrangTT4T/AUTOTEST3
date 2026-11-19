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

from framework.perf.jtl import Stats, read_jtl, stats_by_label


@dataclass(frozen=True)
class Objective:
    label: str
    min_samples: int
    max_error_pct: float
    p95_ms: float | None = None
    p99_ms: float | None = None
    min_throughput_per_s: float | None = None


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
    if profile not in data:
        raise KeyError(
            f"profile {profile!r} not in {path}; profiles: {sorted(k for k in data if k != 'defaults')}"
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
            )
        )
    return objectives


def evaluate(stats: Mapping[str, Stats], objectives: Sequence[Objective]) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for o in objectives:
        s = stats.get(o.label)
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


def to_markdown(stats: Mapping[str, Stats], verdicts: Sequence[Verdict], title: str) -> str:
    lines = [f"# {title}", "", "## Statistics (all labels)", ""]
    lines += [
        "| Label | Samples | Errors % | Mean ms | p50 | p90 | p95 | p99 | Max | Throughput /s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in stats.values():
        cells = [s.label, str(s.count), f"{s.error_pct:.2f}"]
        cells += [f"{v:.0f}" for v in (s.mean_ms, s.p50_ms, s.p90_ms, s.p95_ms, s.p99_ms, s.max_ms)]
        lines.append("| " + " | ".join([*cells, f"{s.throughput_per_s:.2f}"]) + " |")
    failed = [v for v in verdicts if not v.passed]
    lines += ["", f"## Objectives: {'PASSED' if not failed else f'FAILED ({len(failed)})'}", ""]
    lines += ["| Label | Check | Expected | Actual | Result |", "|---|---|---|---|---|"]
    lines += [
        f"| {v.label} | {v.check} | {v.expected} | {v.actual} | {'pass' if v.passed else '**FAIL**'} |"
        for v in verdicts
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.perf.gate", description=__doc__)
    parser.add_argument("jtl", type=Path)
    parser.add_argument("--sla", type=Path, default=Path("perf/sla.toml"))
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", type=Path, default=Path("reports/perf"))
    args = parser.parse_args(argv)
    try:
        objectives = load_objectives(args.sla, args.profile)
        stats = stats_by_label(read_jtl(args.jtl))
    except (OSError, KeyError, ValueError) as error:
        print(f"perf gate: {error}", file=sys.stderr)
        return 2
    verdicts = evaluate(stats, objectives)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"gate-{args.profile}"
    (args.out / f"{stem}.md").write_text(
        to_markdown(stats, verdicts, f"Performance gate - {args.profile}"), encoding="utf-8"
    )
    (args.out / f"{stem}.json").write_text(
        json.dumps(
            {"stats": [asdict(s) for s in stats.values()], "verdicts": [asdict(v) for v in verdicts]},
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
    print(
        f"perf gate {args.profile}: {'PASSED' if not failed else f'FAILED ({len(failed)} objective(s))'}"
        f" -> {args.out / (stem + '.md')}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
