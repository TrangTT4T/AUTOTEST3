"""Client-side performance: measurements, budgets, statistics and the bottleneck verdict.

One measurement = one user interaction timed in the browser session (``login``, ``sort`` ...).
While it runs, the network listener records every request's start and end; afterwards the
union of those intervals is the time the network was busy. Whatever is left is time spent in
the client (JavaScript, rendering, deliberate delays). That split answers the first question
of any performance investigation - *where* does the time go - without access to the server.

Pure logic, unit-tested. The browser-facing recorder lives in swaglabs/app.py.
"""

from __future__ import annotations

import math
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Bottleneck = Literal["client", "network", "mixed"]
# A measurement is "client-bound" when the network was busy for less than this share of it.
CLIENT_BOUND_BELOW = 0.25
NETWORK_BOUND_ABOVE = 0.75


def load_budgets(path: Path) -> dict[str, float]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    budgets = {str(k): float(v) for k, v in data.get("budgets", {}).items()}
    bad = [k for k, v in budgets.items() if v <= 0]
    if bad:
        raise ValueError(f"{path.name}: budgets must be positive milliseconds: {bad}")
    return budgets


def busy_time(intervals: Iterable[tuple[float, float]], start: float, end: float) -> float:
    """Length of the union of ``intervals`` clipped to [start, end] (same unit as the inputs).

    Overlapping requests count once: four parallel 100 ms downloads keep the network busy for
    100 ms, not 400 ms.
    """
    clipped = sorted((max(a, start), min(b, end)) for a, b in intervals if b > start and a < end)
    total = 0.0
    current_start: float | None = None
    current_end = 0.0
    for a, b in clipped:
        if current_start is None or a > current_end:
            if current_start is not None:
                total += current_end - current_start
            current_start, current_end = a, b
        else:
            current_end = max(current_end, b)
    if current_start is not None:
        total += current_end - current_start
    return total


def window_activity(
    finished: Iterable[tuple[float, float]], in_flight_starts: Iterable[float], start: float, end: float
) -> tuple[list[tuple[float, float]], int]:
    """The network activity that belongs to the window [start, end].

    Returns (intervals to count as busy, number of requests started in the window).
    * a finished request counts for the part of it inside the window;
    * an UNFINISHED request counts only if it started inside the window. One that started
      earlier and never reported an end (cancelled by a navigation, served from a cache, a
      long-lived connection) would otherwise make every later interaction look network-bound:
      the instrument would be measuring its own blind spot.
    """
    finished = list(finished)
    in_flight = [(a, end) for a in in_flight_starts if start <= a < end]
    overlapping = [(a, b) for a, b in finished if b > start and a < end]
    started_inside = sum(1 for a, _ in finished if start <= a < end) + len(in_flight)
    return overlapping + in_flight, started_inside


@dataclass(frozen=True)
class Measurement:
    action: str
    duration_ms: float
    network_busy_ms: float
    requests: int
    test: str = ""

    @property
    def client_ms(self) -> float:
        return max(self.duration_ms - self.network_busy_ms, 0.0)

    @property
    def bottleneck(self) -> Bottleneck:
        if self.duration_ms <= 0:
            return "client"
        share = self.network_busy_ms / self.duration_ms
        if share < CLIENT_BOUND_BELOW:
            return "client"
        if share > NETWORK_BOUND_ABOVE:
            return "network"
        return "mixed"

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "client_ms": round(self.client_ms, 1), "bottleneck": self.bottleneck}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Measurement:
        return cls(
            str(data["action"]),
            float(data["duration_ms"]),
            float(data["network_busy_ms"]),
            int(data["requests"]),
            str(data.get("test", "")),
        )


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile (what most load tools report): p95 of 20 samples is the 19th."""
    if not values:
        raise ValueError("no values")
    if not 0 < pct <= 100:
        raise ValueError(f"percentile must be in (0, 100], got {pct}")
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


@dataclass(frozen=True)
class ActionStats:
    action: str
    samples: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    budget_ms: float | None
    bottleneck: Bottleneck

    @property
    def within_budget(self) -> bool | None:
        return None if self.budget_ms is None else self.p95_ms <= self.budget_ms


def summarise(measurements: Iterable[Measurement], budgets: Mapping[str, float]) -> list[ActionStats]:
    by_action: dict[str, list[Measurement]] = defaultdict(list)
    for m in measurements:
        by_action[m.action].append(m)
    stats = []
    for action in sorted(by_action):
        items = by_action[action]
        durations = [m.duration_ms for m in items]
        # The slowest sample is the one worth explaining: its split names the bottleneck.
        slowest = max(items, key=lambda m: m.duration_ms)
        stats.append(
            ActionStats(
                action=action,
                samples=len(items),
                p50_ms=percentile(durations, 50),
                p95_ms=percentile(durations, 95),
                max_ms=max(durations),
                budget_ms=budgets.get(action),
                bottleneck=slowest.bottleneck,
            )
        )
    return stats


def to_markdown(stats: Sequence[ActionStats], persona: str) -> str:
    lines = [
        f"# Interaction timings - {persona}",
        "",
        "| Action | Samples | p50 ms | p95 ms | Max ms | Budget ms | Verdict | Slowest sample bound by |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for s in stats:
        verdict = {None: "no budget", True: "OK", False: "OVER BUDGET"}[s.within_budget]
        budget = "-" if s.budget_ms is None else f"{s.budget_ms:.0f}"
        lines.append(
            f"| {s.action} | {s.samples} | {s.p50_ms:.0f} | {s.p95_ms:.0f} | {s.max_ms:.0f} "
            f"| {budget} | {verdict} | {s.bottleneck} |"
        )
    lines += [
        "",
        (
            "*client* = the network was idle for most of the interaction (JavaScript, rendering or a "
            "deliberate delay); *network* = waiting for responses; *mixed* = both."
        ),
    ]
    return "\n".join(lines) + "\n"
