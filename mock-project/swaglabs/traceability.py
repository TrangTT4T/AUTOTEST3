"""Traceability matrix: requirement -> declared scenarios -> run outcomes -> status.

Pure logic, unit-tested. swaglabs/plugins/traceability.py collects the inputs and writes
reports/traceability.{md,json}; swaglabs/matrix.py merges the JSON of several persona runs.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from swaglabs.requirements import Requirement, area_tags, requirement_tags

OUTCOMES = ("passed", "failed", "known-defect", "skipped")
# The worst outcome decides. A known defect (strict xfail) is a requirement NOT met.
STATUS_PRECEDENCE = (
    ("failed", "FAIL"),
    ("known-defect", "KNOWN DEFECT"),
    ("passed", "PASS"),
    ("skipped", "MANUAL"),
)
NOT_COVERED = "NOT COVERED"
NOT_RUN = "NOT RUN"


@dataclass(frozen=True)
class DeclaredScenario:
    feature: str
    name: str
    tags: frozenset[str]

    @property
    def requirements(self) -> list[str]:
        return requirement_tags(self.tags)

    @property
    def areas(self) -> list[str]:
        return area_tags(self.tags)


def declared_scenarios(features_dir: Path) -> list[DeclaredScenario]:
    """Every scenario in the .feature files with its effective tags (feature + rule + scenario + examples)."""
    found = []
    for path in sorted(features_dir.rglob("*.feature")):
        document: Any = Parser().parse(TokenScanner(path.read_text(encoding="utf-8")))
        feature = document["feature"]
        inherited = _names(feature["tags"])
        for scenario, tags in _scenarios(feature["children"], inherited):
            found.append(DeclaredScenario(path.name, scenario["name"], frozenset(tags)))
    return found


def _names(tags: Iterable[Mapping[str, str]]) -> set[str]:
    return {t["name"].lstrip("@") for t in tags}


def _scenarios(children: Iterable[Any], inherited: set[str]) -> Iterator[tuple[Any, set[str]]]:
    for child in children:
        if "scenario" in child:
            scenario = child["scenario"]
            tags = inherited | _names(scenario["tags"])
            for examples in scenario.get("examples", []):
                tags |= _names(examples["tags"])  # examples' areas count for the whole outline
            yield scenario, tags
        elif "rule" in child:
            yield from _scenarios(child["rule"]["children"], inherited | _names(child["rule"]["tags"]))


def requirement_index(scenarios: Iterable[DeclaredScenario]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for scenario in scenarios:
        for req in scenario.requirements:
            index.setdefault(req, []).append(f"{scenario.feature}: {scenario.name}")
    return index


@dataclass(frozen=True)
class Row:
    requirement: Requirement
    declared: int
    outcomes: Mapping[str, int]
    status: str

    def as_dict(self) -> dict[str, Any]:
        r = self.requirement
        return {
            "id": r.id,
            "title": r.title,
            "risk": r.risk,
            "declared": self.declared,
            "outcomes": dict(self.outcomes),
            "status": self.status,
        }


def status_of(declared: int, outcomes: Mapping[str, int]) -> str:
    if declared == 0:
        return NOT_COVERED
    return next((status for outcome, status in STATUS_PRECEDENCE if outcomes.get(outcome)), NOT_RUN)


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


def to_markdown(rows: Iterable[Row], title: str) -> str:
    header = [
        "Requirement",
        "Risk",
        "Title",
        "Scenarios",
        "Passed",
        "Failed",
        "Known defect",
        "Manual",
        "Status",
    ]
    lines = [f"# {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        o = row.outcomes
        cells = [
            row.requirement.id,
            row.requirement.risk,
            row.requirement.title,
            row.declared,
            o["passed"],
            o["failed"],
            o["known-defect"],
            o["skipped"],
            f"**{row.status}**",
        ]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    return "\n".join(lines) + "\n"
