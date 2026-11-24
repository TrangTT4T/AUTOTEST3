"""Read JMeter results (JTL, CSV format) and compute per-label statistics. Pure and unit-tested."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    start_ms: int
    elapsed_ms: int
    label: str
    success: bool
    code: str
    message: str
    threads: int
    thread: str = ""  # thread name: "<thread group> 1-3" (optional column)

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.elapsed_ms


REQUIRED_COLUMNS = ("timeStamp", "elapsed", "label", "responseCode", "success", "allThreads")


def read_jtl(path: Path) -> list[Sample]:
    """JMeter CSV results (format pinned by perf/jmeter.properties); quoted messages may contain commas.

    Fails closed: a file without the columns the analysis needs is an error, never "no samples".
    """
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{path}: missing JTL columns {missing}; run JMeter with -q perf/jmeter.properties"
            )
        return [
            Sample(
                start_ms=int(row["timeStamp"]),
                elapsed_ms=int(row["elapsed"]),
                label=row["label"],
                success=row["success"].strip().lower() == "true",
                code=row["responseCode"],
                message=row.get("failureMessage") or row.get("responseMessage") or "",
                threads=int(row.get("allThreads") or 0),
                thread=row.get("threadName") or "",
            )
            for row in reader
        ]


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..100): an observed value, never an interpolation."""
    if not values:
        return math.nan
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return float(ordered[rank - 1])


@dataclass(frozen=True)
class Stats:
    label: str
    count: int
    errors: int
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    throughput_per_s: float

    @property
    def error_pct(self) -> float:
        return 100.0 * self.errors / self.count if self.count else 0.0


def stats_for(label: str, samples: Sequence[Sample]) -> Stats:
    times = [s.elapsed_ms for s in samples]
    span_s = (max(s.end_ms for s in samples) - min(s.start_ms for s in samples)) / 1000 if samples else 0
    return Stats(
        label=label,
        count=len(samples),
        errors=sum(not s.success for s in samples),
        mean_ms=sum(times) / len(times) if times else math.nan,
        p50_ms=percentile(times, 50),
        p90_ms=percentile(times, 90),
        p95_ms=percentile(times, 95),
        p99_ms=percentile(times, 99),
        max_ms=float(max(times)) if times else math.nan,
        throughput_per_s=len(samples) / span_s if span_s > 0 else math.nan,
    )


def stats_by_label(samples: Iterable[Sample]) -> dict[str, Stats]:
    groups: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        groups[sample.label].append(sample)
    return {label: stats_for(label, group) for label, group in sorted(groups.items())}


@dataclass(frozen=True)
class Window:
    """The part of a run that is analysed: the steady state between ramp-up and ramp-down."""

    start_s: float  # seconds after the first load sample started
    end_s: float
    kept: int
    total: int


def steady_state(
    samples: Sequence[Sample], *, skip_head_s: float, skip_tail_s: float, thread_prefix: str = ""
) -> tuple[list[Sample], Window]:
    """Samples of the load threads that start after the ramp-up and end before the ramp-down.

    Ramp-up samples meet cold caches and growing load; ramp-down samples meet a draining system.
    Mixing them into the steady state hides or invents problems (CT-PT 4.3, 4.4).
    """
    load = [s for s in samples if s.thread.startswith(thread_prefix)]
    if not load:
        return [], Window(0.0, 0.0, 0, 0)
    origin = min(s.start_ms for s in load)
    finish = max(s.end_ms for s in load)
    start_ms = origin + skip_head_s * 1000
    end_ms = finish - skip_tail_s * 1000
    kept = [s for s in load if s.start_ms >= start_ms and s.end_ms <= end_ms]
    return kept, Window((start_ms - origin) / 1000, (end_ms - origin) / 1000, len(kept), len(load))


def response_codes(samples: Iterable[Sample]) -> dict[str, dict[str, int]]:
    """label -> response code -> count (transaction samples have no code: shown as "-")."""
    codes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in samples:
        codes[s.label][s.code or "-"] += 1
    return {label: dict(sorted(c.items())) for label, c in sorted(codes.items())}


@dataclass(frozen=True)
class Bucket:
    start_s: int  # seconds since the first sample started
    count: int
    errors: int
    p95_ms: float
    threads: int


def timeline(samples: Sequence[Sample], label: str, bucket_s: int = 5) -> list[Bucket]:
    """Completed samples of ``label`` per time bucket (by end time), with the active thread count."""
    if not samples:
        return []
    origin = min(s.start_ms for s in samples)
    groups: dict[int, list[Sample]] = defaultdict(list)
    for s in samples:
        if s.label == label:
            groups[(s.end_ms - origin) // 1000 // bucket_s * bucket_s].append(s)
    return [
        Bucket(
            start,
            len(group),
            sum(not s.success for s in group),
            percentile([s.elapsed_ms for s in group], 95),
            max(s.threads for s in group),
        )
        for start, group in sorted(groups.items())
    ]
