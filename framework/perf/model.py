"""Workload model: from an operational profile to a load profile (ISTQB CT-PT 4.2.3-4.2.5).

Two laws do all the work, both in a steady state:

* Little's law                  N = X x (R + Z)
* Interactive response-time law X = N / (R + Z)

N = concurrent users (virtual users busy in a journey or thinking), X = throughput (journeys
per second), R = response time of the journey, Z = think time. The same 500 users produce
500 / 60 s = 8.3 requests/s when each waits a minute between requests, and 500/s when they do
not wait at all: concurrency alone says nothing about load.

    python -m framework.perf.model perf/workload.toml

Pure and unit-tested (tests/unit/test_perf.py).
"""

from __future__ import annotations

import argparse
import math
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SHARE_TOLERANCE = 1e-6


def throughput(users: float, response_s: float, think_s: float) -> float:
    """X = N / (R + Z): journeys per second that ``users`` generate in a closed workload."""
    cycle = response_s + think_s
    if users < 0 or cycle <= 0:
        raise ValueError("users must be >= 0 and response + think time > 0")
    return users / cycle


def concurrency(rate_per_s: float, response_s: float, think_s: float) -> float:
    """N = X x (R + Z): users busy at once when journeys arrive at ``rate_per_s``."""
    if rate_per_s < 0 or response_s < 0 or think_s < 0:
        raise ValueError("rate, response time and think time must be >= 0")
    return rate_per_s * (response_s + think_s)


@dataclass(frozen=True)
class Journey:
    key: str
    name: str
    share: float
    response_s: float
    think_s: float


@dataclass(frozen=True)
class LoadProfile:
    peak_journeys_per_s: float
    rampup_s: int
    steady_s: int
    rampdown_s: int

    @property
    def total_s(self) -> int:
        return self.rampup_s + self.steady_s + self.rampdown_s

    def journeys_started(self) -> float:
        """Expected journeys in a whole run: half the peak rate during each linear ramp."""
        return self.peak_journeys_per_s * (self.steady_s + (self.rampup_s + self.rampdown_s) / 2)


@dataclass(frozen=True)
class Row:
    journey: Journey
    rate_per_s: float
    users: float


@dataclass(frozen=True)
class Workload:
    source: str
    journeys: tuple[Journey, ...]
    load: LoadProfile

    def rows(self) -> list[Row]:
        rows = []
        for j in self.journeys:
            rate = self.load.peak_journeys_per_s * j.share
            rows.append(Row(j, rate, concurrency(rate, j.response_s, j.think_s)))
        return rows


def load_workload(path: Path) -> Workload:
    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    profile = data["operational_profile"]
    journeys = tuple(
        Journey(key, str(j["name"]), float(j["share"]), float(j["response_s"]), float(j["think_s"]))
        for key, j in profile["journeys"].items()
    )
    total = sum(j.share for j in journeys)
    if not journeys or abs(total - 1.0) > SHARE_TOLERANCE:
        raise ValueError(f"{path.name}: journey shares must add up to 1.0, got {total:g}")
    load = data["load_profile"]
    profile_ = LoadProfile(
        float(load["peak_journeys_per_s"]),
        int(load["rampup_s"]),
        int(load["steady_s"]),
        int(load["rampdown_s"]),
    )
    if profile_.peak_journeys_per_s <= 0 or profile_.steady_s <= 0:
        raise ValueError(f"{path.name}: the peak rate and the steady state must be positive")
    return Workload(str(profile.get("source", "")), journeys, profile_)


def jmeter_properties(workload: Workload) -> dict[str, str]:
    """The -J properties that make perf/orders_sandbox_profile.jmx run THIS load profile."""
    order = next((j for j in workload.journeys if j.key == "J1"), None)
    if order is None:
        raise ValueError("the profile needs journey J1 (the order journey)")
    load = workload.load
    return {
        "rate": f"{load.peak_journeys_per_s:g}",
        "rampup": str(load.rampup_s),
        "steady": str(load.steady_s),
        "rampdown": str(load.rampdown_s),
        "order_pct": str(round(order.share * 100)),
    }


def to_markdown(workload: Workload) -> str:
    load = workload.load
    lines = [
        "# Load profile (derived from the operational profile)",
        "",
        f"Source of the operational profile: {workload.source}",
        "",
        "| Journey | Share | Rate /s at peak | R s | Z s | Concurrent users N = X(R+Z) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    rows = workload.rows()
    for r in rows:
        j = r.journey
        lines.append(
            f"| {j.name} | {j.share:.0%} | {r.rate_per_s:.2f} | {j.response_s:g} | {j.think_s:g} "
            f"| {r.users:.1f} |"
        )
    total_users = sum(r.users for r in rows)
    lines += [
        (
            f"| **Total** | 100% | {load.peak_journeys_per_s:.2f} | | | **{total_users:.1f}** "
            f"(size the load generator for {math.ceil(total_users * 2)}: x2 headroom) |"
        ),
        "",
        (
            f"Shape: ramp-up {load.rampup_s} s -> steady {load.steady_s} s at {load.peak_journeys_per_s:g} "
            f"journeys/s -> ramp-down {load.rampdown_s} s ({load.total_s} s, "
            f"~{load.journeys_started():.0f} journeys)."
        ),
        "",
        "```",
        "jmeter -n -t perf/orders_sandbox_profile.jmx -q perf/jmeter.properties -l reports/perf/profile.jtl "
        + " ".join(f"-J{k}={v}" for k, v in jmeter_properties(workload).items()),
        "```",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.perf.model", description=__doc__)
    parser.add_argument("workload", type=Path, nargs="?", default=Path("perf/workload.toml"))
    args = parser.parse_args(argv)
    try:
        workload = load_workload(args.workload)
    except (OSError, KeyError, ValueError) as error:
        print(f"workload model: {error}", file=sys.stderr)
        return 2
    print(to_markdown(workload), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
