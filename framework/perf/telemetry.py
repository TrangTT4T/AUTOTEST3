"""Sample the sandbox's /metrics during a load test: the local stand-in for CloudWatch metrics.

    python -m framework.perf.telemetry http://127.0.0.1:8765 --out reports/perf/telemetry.csv --duration 70

One row per subscription per sample: wall-clock time, queued, in flight, processed (cumulative), failed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

FIELDS = ("wall_ms", "subscription", "queued", "in_flight", "processed", "failed", "workers")


def rows_from(metrics: dict[str, Any], wall_ms: int) -> list[dict[str, Any]]:
    return [
        {"wall_ms": wall_ms, "subscription": name, **{k: values[k] for k in FIELDS[2:]}}
        for name, values in sorted(metrics["subscriptions"].items())
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.perf.telemetry", description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args(argv)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.duration
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        while time.monotonic() < deadline:
            started = time.monotonic()
            with opener.open(f"{args.url.rstrip('/')}/metrics", timeout=5) as response:
                writer.writerows(rows_from(json.load(response), int(time.time() * 1000)))
            f.flush()
            time.sleep(max(0.0, args.interval - (time.monotonic() - started)))  # sampling period
    return 0


if __name__ == "__main__":
    sys.exit(main())
