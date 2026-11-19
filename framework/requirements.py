"""Requirement registry (requirements.toml) and the tag rules built on it."""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Risk = Literal["low", "medium", "high"]
RISK_ORDER: dict[str, int] = {"low": 1, "medium": 2, "high": 3}
SUITE_TAGS = frozenset({"smoke", "regression"})
PLATFORM_TAGS = frozenset({"web", "api", "mobile", "events"})


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    risk: Risk


def load_registry(path: Path) -> dict[str, Requirement]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    registry: dict[str, Requirement] = {}
    for req_id, entry in data.items():
        risk = entry["risk"]
        if risk not in RISK_ORDER:
            raise ValueError(f"{req_id}: unknown risk {risk!r}")
        registry[req_id] = Requirement(req_id, entry["title"], risk)
    return registry


def tag_problems(tags: Iterable[str], registry: Mapping[str, Requirement]) -> list[str]:
    """Return every broken tag rule for one scenario (empty list = valid).

    Pure function: no pytest, no files. Unit-tested in tests/unit.
    """
    tags = set(tags)
    problems: list[str] = []
    reqs = sorted(t for t in tags if t.startswith("REQ-"))

    if not reqs:
        problems.append("no @REQ-xx tag")
    unknown = [r for r in reqs if r not in registry]
    if unknown:
        problems.append(f"unknown requirement(s) {unknown} - add them to requirements.toml")
    if not tags & PLATFORM_TAGS:
        problems.append(f"no platform tag (one of {sorted(PLATFORM_TAGS)})")

    if "manual" in tags:
        return problems  # manual scenarios need no risk or suite tag

    risks = sorted(t.removeprefix("risk-") for t in tags if t.startswith("risk-"))
    if len(risks) != 1:
        problems.append(f"needs exactly one @risk-* tag, found {['risk-' + r for r in risks]}")
    elif reqs and not unknown:
        expected = max((registry[r].risk for r in reqs), key=RISK_ORDER.__getitem__)
        if risks[0] != expected:
            problems.append(f"@risk-{risks[0]} but registry says {expected} for {reqs}")

    suites = sorted(tags & SUITE_TAGS)
    if len(suites) != 1:
        problems.append(f"needs exactly one of @smoke/@regression, found {suites}")
    return problems
