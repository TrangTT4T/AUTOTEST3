"""Merge the traceability of several runs into one persona x requirement quality matrix.

    python -m swaglabs.matrix reports-*/traceability.json > quality-matrix.md

Every CI matrix job (one persona/browser each) writes its own traceability.json; this tool
puts them side by side, which is the release view: "which requirement holds for which kind of
user, and which known defect stops it".
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SYMBOL = {
    "PASS": "PASS",
    "FAIL": "**FAIL**",
    "KNOWN DEFECT": "DEFECT",
    "MANUAL": "manual",
    "NOT RUN": "-",
    "NOT COVERED": "**NOT COVERED**",
}


def load(paths: Sequence[Path]) -> list[dict[str, Any]]:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    return sorted(runs, key=lambda r: str(r["label"]))


def merge(runs: Sequence[dict[str, Any]]) -> str:
    """Markdown table: one row per requirement, one column per run."""
    if not runs:
        raise ValueError("no traceability.json files given")
    labels = [str(r["label"]) for r in runs]
    titles: dict[str, str] = {}
    statuses: dict[str, dict[str, str]] = {}
    for run in runs:
        for row in run["rows"]:
            titles.setdefault(row["id"], row["title"])
            statuses.setdefault(row["id"], {})[run["label"]] = row["status"]
    lines = [
        "# Quality matrix (requirement x run)",
        "",
        "| Requirement | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for req_id in sorted(titles):
        cells = [SYMBOL.get(statuses[req_id].get(label, "NOT RUN"), "?") for label in labels]
        lines.append(f"| {req_id} {titles[req_id]} | " + " | ".join(cells) + " |")
    failing = [label for label, run in zip(labels, runs, strict=True) if _has(run, "FAIL")]
    defects = sorted({d for run in runs for d in run.get("known_defects", [])})
    lines += [
        "",
        f"Known defects observed: {', '.join(defects) if defects else 'none'}.",
        f"Runs with unexpected failures: {', '.join(failing) if failing else 'none'}.",
    ]
    return "\n".join(lines) + "\n"


def _has(run: dict[str, Any], status: str) -> bool:
    return any(row["status"] == status for row in run["rows"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="traceability.json of each run")
    args = parser.parse_args(argv)
    runs = load(args.files)
    print(merge(runs), end="")
    # Exit 1 when any run has an unexpected failure, so a pipeline can gate on the merged view.
    return 1 if any(_has(run, "FAIL") for run in runs) else 0


if __name__ == "__main__":
    sys.exit(main())
