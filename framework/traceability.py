"""Traceability matrix: requirement -> declared scenarios -> run outcomes.

Pure logic, unit-tested in tests/unit. The pytest plugin only collects
inputs and writes outputs.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from framework.requirements import Requirement

OUTCOMES = ("passed", "failed", "known-defect", "blocked", "skipped")


def declared_scenarios(features_dir: Path) -> dict[str, list[str]]:
    """Scan .feature files: requirement id -> names of scenarios that declare it."""
    declared: dict[str, list[str]] = {}
    for path in sorted(features_dir.rglob("*.feature")):
        document: Any = Parser().parse(TokenScanner(path.read_text(encoding="utf-8")))
        feature = document["feature"]
        feature_tags = {t["name"].lstrip("@") for t in feature["tags"]}
        for scenario in _scenarios(feature["children"]):
            tags = feature_tags | {t["name"].lstrip("@") for t in scenario["tags"]}
            for req in sorted(t for t in tags if t.startswith("REQ-")):
                declared.setdefault(req, []).append(f"{path.name}: {scenario['name']}")
    return declared


def _scenarios(children: Iterable[Any]) -> Iterable[Any]:
    for child in children:
        if "scenario" in child:
            yield child["scenario"]
        elif "rule" in child:
            yield from _scenarios(child["rule"]["children"])


@dataclass(frozen=True)
class Row:
    requirement: Requirement
    declared: int
    outcomes: Mapping[str, int]
    status: str

    def cells(self) -> list[str | int]:
        r = self.requirement
        return [r.id, r.risk, r.title, self.declared, *(self.outcomes[o] for o in OUTCOMES), self.status]


HEADER = [
    "Requirement",
    "Risk",
    "Title",
    "Declared",
    "Passed",
    "Failed",
    "Known defect",
    "Blocked",
    "Manual/Skipped",
    "Status",
]


# The worst outcome decides. A known defect (strict xfail) is a requirement NOT met, never "manual".
STATUS_PRECEDENCE = (
    ("failed", "FAIL"),
    ("known-defect", "KNOWN DEFECT"),
    ("blocked", "BLOCKED"),
    ("passed", "PASS"),
    ("skipped", "MANUAL"),
)


def status_of(declared: int, outcomes: Mapping[str, int]) -> str:
    if declared == 0:
        return "NOT COVERED"
    return next((status for outcome, status in STATUS_PRECEDENCE if outcomes[outcome]), "NOT RUN")


def build_matrix(
    registry: Mapping[str, Requirement],
    declared: Mapping[str, list[str]],
    results: Iterable[tuple[Iterable[str], str]],
) -> list[Row]:
    """``results``: one (requirement ids, outcome) pair per executed test."""
    counts: dict[str, Counter[str]] = {req: Counter() for req in registry}
    for req_ids, outcome in results:
        for req_id in req_ids:
            counts.setdefault(req_id, Counter())[outcome] += 1
    rows = []
    for req_id, req in registry.items():
        outcomes = {o: counts[req_id][o] for o in OUTCOMES}
        n_declared = len(declared.get(req_id, []))
        rows.append(Row(req, n_declared, outcomes, status_of(n_declared, outcomes)))
    return rows


def to_markdown(rows: list[Row]) -> str:
    lines = ["| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
    lines += ["| " + " | ".join(str(c) for c in row.cells()) + " |" for row in rows]
    return "\n".join(lines) + "\n"
