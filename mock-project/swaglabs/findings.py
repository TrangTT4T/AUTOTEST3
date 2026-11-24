"""Findings register (findings.toml): which persona is expected to break which behaviour.

Pure logic, unit-tested. The pytest plugin (swaglabs/plugins/findings.py) turns the answer of
``expected_failures`` into strict xfail markers.
"""

from __future__ import annotations

import tomllib
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from swaglabs.personas import Persona

Severity = Literal["critical", "major", "minor"]
SEVERITIES: tuple[Severity, ...] = ("critical", "major", "minor")


@dataclass(frozen=True)
class Finding:
    id: str
    title: str
    personas: frozenset[Persona]
    area: str
    requirement: str
    severity: Severity

    def affects(self, persona: Persona, areas: Collection[str]) -> bool:
        return persona in self.personas and self.area in areas


@dataclass(frozen=True)
class Register:
    areas: Mapping[str, str]  # area -> what it means
    findings: tuple[Finding, ...]

    def expected_failures(self, persona: Persona, areas: Collection[str]) -> list[Finding]:
        """The findings that must make a scenario with these areas fail when run as ``persona``."""
        return [f for f in self.findings if f.affects(persona, areas)]

    def by_id(self, finding_id: str) -> Finding:
        for finding in self.findings:
            if finding.id == finding_id:
                return finding
        raise KeyError(finding_id)

    def untested(self, used_areas: Iterable[str]) -> list[str]:
        """Finding ids whose area no scenario declares: nothing would ever detect a fix."""
        used = set(used_areas)
        return [f.id for f in self.findings if f.area not in used]


def load_register(path: Path, requirement_ids: Collection[str]) -> Register:
    """Read and validate findings.toml: every reference must resolve, or the run refuses to start."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    areas = {str(k): str(v) for k, v in data.pop("areas", {}).items()}
    findings: list[Finding] = []
    for finding_id, entry in data.items():
        problems = _problems(finding_id, entry, areas, requirement_ids)
        if problems:
            raise ValueError(f"{path.name} [{finding_id}]: " + "; ".join(problems))
        findings.append(
            Finding(
                id=finding_id,
                title=str(entry["title"]),
                personas=frozenset(Persona(p) for p in entry["personas"]),
                area=str(entry["area"]),
                requirement=str(entry["requirement"]),
                severity=cast(Severity, entry["severity"]),
            )
        )
    return Register(areas, tuple(findings))


def _problems(
    finding_id: str, entry: Mapping[str, object], areas: Mapping[str, str], requirement_ids: Collection[str]
) -> list[str]:
    problems = []
    if not finding_id.startswith("SL-"):
        problems.append("ids start with 'SL-'")
    personas = entry.get("personas")
    if not isinstance(personas, list) or not personas:
        problems.append("needs a non-empty personas list")
    else:
        valid = {p.value for p in Persona.runnable()}
        problems += [f"unknown or non-runnable persona {p!r}" for p in personas if p not in valid]
    if entry.get("area") not in areas:
        problems.append(f"area {entry.get('area')!r} is not declared in [areas]")
    if entry.get("requirement") not in requirement_ids:
        problems.append(f"requirement {entry.get('requirement')!r} is not in requirements.toml")
    if entry.get("severity") not in SEVERITIES:
        problems.append(f"severity must be one of {SEVERITIES}")
    if not entry.get("title"):
        problems.append("needs a title")
    return problems
