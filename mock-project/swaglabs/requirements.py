"""Requirement registry (requirements.toml) and the tag rules every scenario must follow."""

from __future__ import annotations

import tomllib
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Risk = Literal["low", "medium", "high"]
RISK_ORDER: dict[str, int] = {"low": 1, "medium": 2, "high": 3}
SUITE_TAGS = frozenset({"smoke", "regression"})
REQUIREMENT_PREFIX = "REQ-"
AREA_PREFIX = "area-"


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    risk: Risk


def load_registry(path: Path) -> dict[str, Requirement]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    registry: dict[str, Requirement] = {}
    for req_id, entry in data.items():
        if not req_id.startswith(REQUIREMENT_PREFIX):
            raise ValueError(
                f"{path.name}: requirement ids start with {REQUIREMENT_PREFIX!r}, got {req_id!r}"
            )
        risk = entry["risk"]
        if risk not in RISK_ORDER:
            raise ValueError(f"{req_id}: unknown risk {risk!r}")
        registry[req_id] = Requirement(req_id, str(entry["title"]), cast(Risk, risk))
    return registry


def requirement_tags(tags: Iterable[str]) -> list[str]:
    return sorted(t for t in tags if t.startswith(REQUIREMENT_PREFIX))


def area_tags(tags: Iterable[str]) -> list[str]:
    return sorted(t.removeprefix(AREA_PREFIX) for t in tags if t.startswith(AREA_PREFIX))


def tag_problems(
    tags: Iterable[str], registry: Mapping[str, Requirement], known_areas: Collection[str]
) -> list[str]:
    """Every broken tag rule for one scenario (empty list = valid).

    Pure function: no pytest, no files. Unit-tested in tests/unit/test_requirements.py.
    """
    tags = set(tags)
    problems: list[str] = []
    reqs = requirement_tags(tags)
    if not reqs:
        problems.append("no @REQ-xx tag")
    unknown = [r for r in reqs if r not in registry]
    if unknown:
        problems.append(f"unknown requirement(s) {unknown} - add them to requirements.toml")
    unknown_areas = [a for a in area_tags(tags) if a not in known_areas]
    if unknown_areas:
        problems.append(f"unknown area(s) {unknown_areas} - declare them in findings.toml [areas]")
    if "manual" in tags:
        return problems  # a manual check needs no risk or suite tag

    risks = sorted(t.removeprefix("risk-") for t in tags if t.startswith("risk-"))
    if len(risks) != 1:
        problems.append(f"needs exactly one @risk-* tag, found {['risk-' + r for r in risks]}")
    elif reqs and not unknown:
        expected = max((registry[r].risk for r in reqs), key=RISK_ORDER.__getitem__)
        if risks[0] != expected:
            problems.append(f"@risk-{risks[0]} but the registry says {expected} for {reqs}")
    suites = sorted(tags & SUITE_TAGS)
    if len(suites) != 1:
        problems.append(f"needs exactly one of @smoke/@regression, found {suites}")
    return problems
