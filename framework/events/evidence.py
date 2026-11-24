"""Evidence for asynchronous tests: per-flow files on failure, and the run's evidence record.

The record follows the template of Day 10, Part 7.3 and is written for every events test,
passed or not: it is the execution evidence the lab asks for.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.events import oracles
from framework.events.flow import OrderFlow

log = logging.getLogger("shop.events")
REPEAT_REASONS = {"duplicate", "redelivery (no ack)"}
COLUMNS = (
    "Test",
    "Correlation id",
    "Fault",
    "Oracle",
    "Result",
    "Measured convergence (s)",
    "Attempts seen",
    "Duplicates seen",
    "Charges",
)


def collect(flow: OrderFlow, folder: Path, sandbox_log: Path | None) -> list[Path]:
    """Write everything about one flow; one file that cannot be read never hides the failure."""
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    cid = flow.correlation_id

    def save(name: str, produce: Any) -> None:
        try:
            content = produce()
            path = folder / name
            path.write_text(content if isinstance(content, str) else json.dumps(content, indent=2), "utf-8")
            written.append(path)
        except Exception as error:  # noqa: BLE001 - evidence must never replace the original failure
            log.warning("could not collect %s for %s: %r", name, cid, error)

    save("deliveries.txt", lambda: "\n".join(d.describe() for d in flow.deliveries()) + "\n")
    save("deliveries.json", lambda: flow.api.observe.raw("/deliveries", cid))
    save("events.json", lambda: flow.api.observe.raw("/events", cid))
    save("payments.json", lambda: flow.api.observe.raw("/payments", cid))
    save("dlq.json", lambda: flow.api.observe.raw("/dlq", cid))
    save("frames.json", lambda: [f.__dict__ for f in flow.stream.frames])
    save("order.json", lambda: flow.view().__dict__ if flow.order_id and flow.view() else None)
    save("faults.json", lambda: [f.to_json(cid) for f in flow.faults])
    if sandbox_log is not None:
        save("sandbox_log.txt", lambda: _lines_with(sandbox_log, cid))
    return written


def _lines_with(path: Path, text: str) -> str:
    with path.open(encoding="utf-8", errors="replace") as log_file:
        return "".join(line for line in log_file if text in line)


def row(test: str, oracle: str, flows: Iterable[OrderFlow], result: str) -> dict[str, str]:
    flows = list(flows)
    deliveries = [d for flow in flows for d in _safe_deliveries(flow)]
    charges = sum(len(_safe(flow.charges)) for flow in flows)
    converged = [flow.converged_in for flow in flows if flow.converged_in is not None]
    return {
        "Test": test,
        "Correlation id": ", ".join(flow.correlation_id for flow in flows),
        "Fault": "; ".join(f.describe() for flow in flows for f in flow.faults) or "none",
        "Oracle": oracle,
        "Result": result,
        "Measured convergence (s)": ", ".join(f"{c:.3f}" for c in converged) or "-",
        "Attempts seen": str(oracles.max_attempt(deliveries)),
        "Duplicates seen": str(sum(d.reason in REPEAT_REASONS for d in deliveries)),
        "Charges": str(charges),
    }


def _safe(read: Any) -> list[Any]:
    try:
        return list(read())
    except Exception:  # noqa: BLE001 - the system may be gone after a crash: the row still gets written
        return []


def _safe_deliveries(flow: OrderFlow) -> list[Any]:
    return _safe(flow.deliveries)


def to_markdown(rows: Iterable[Mapping[str, str]], header: Mapping[str, str]) -> str:
    rows = sorted(rows, key=lambda r: r["Test"])
    lines = [
        f"# Async execution evidence — {datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ}",
        "",
        "| Field | Value |",
        "|---|---|",
        *(f"| {k} | {v} |" for k, v in header.items()),
        f"| Tests | {len(rows)}: " + ", ".join(_counts(rows)) + " |",
        "",
        "## Per test",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "---|" * len(COLUMNS),
        *("| " + " | ".join(r[c].replace("|", "/") for c in COLUMNS) + " |" for r in rows),
        "",
        "## Event log excerpts",
        "Failed and known-defect flows: `reports/events/<test>/deliveries.txt` (ordered by time,",
        "with subscription, event, sequence, delivery number, reason, and result).",
        "",
    ]
    return "\n".join(lines)


def _counts(rows: list[Mapping[str, str]]) -> list[str]:
    counts: dict[str, int] = {}
    for r in rows:
        key = r["Result"].split(" ")[0]
        counts[key] = counts.get(key, 0) + 1
    return [f"{n} {k}" for k, n in sorted(counts.items())]
