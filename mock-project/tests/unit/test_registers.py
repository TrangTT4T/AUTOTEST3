"""The real registers in this repository load, agree with each other and with the docs."""

from pathlib import Path

import pytest

from swaglabs.findings import Finding, Register, load_register
from swaglabs.personas import Persona
from swaglabs.requirements import load_registry, tag_problems
from swaglabs.traceability import declared_scenarios, requirement_index

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def registry() -> dict[str, object]:
    return dict(load_registry(ROOT / "requirements.toml"))


@pytest.fixture(scope="module")
def register(registry: dict[str, object]) -> Register:
    return load_register(ROOT / "findings.toml", registry)


def test_every_requirement_has_a_scenario(registry: dict[str, object]) -> None:
    index = requirement_index(declared_scenarios(ROOT / "features"))
    assert sorted(set(registry) - set(index)) == []


def test_every_finding_can_be_detected(register: Register) -> None:
    used = {area for s in declared_scenarios(ROOT / "features") for area in s.areas}
    assert register.untested(used) == []
    assert sorted(set(register.areas) - used) == [], "declared areas nobody tags"


def test_every_finding_is_documented(register: Register) -> None:
    report = (ROOT / "docs" / "03-findings.md").read_text(encoding="utf-8")
    missing = [f.id for f in register.findings if f"### {f.id} " not in report]
    assert missing == []


def test_feature_files_follow_the_tag_rules(register: Register) -> None:
    reg = load_registry(ROOT / "requirements.toml")
    problems = [
        f"{s.feature}: {s.name}: {p}"
        for s in declared_scenarios(ROOT / "features")
        for p in tag_problems(s.tags, reg, register.areas)
    ]
    assert problems == []


def test_standard_user_is_only_hit_by_findings_that_hit_everyone(register: Register) -> None:
    for finding in register.findings:
        if Persona.STANDARD in finding.personas:
            assert finding.personas == frozenset(Persona.runnable()), finding.id


def test_expected_failures_join_persona_and_area(register: Register) -> None:
    ids = [f.id for f in register.expected_failures(Persona.ERROR, ["sorting", "unrelated"])]
    assert ids == ["SL-03"]
    assert register.expected_failures(Persona.STANDARD, ["sorting"]) == []
    finding: Finding = register.by_id("SL-04")
    assert finding.affects(Persona.PROBLEM, ["add-any-product"])
    with pytest.raises(KeyError):
        register.by_id("SL-99")
