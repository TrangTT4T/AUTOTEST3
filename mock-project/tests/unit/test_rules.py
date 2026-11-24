"""Requirement registry, tag rules and the findings loader: what they accept and refuse."""

from pathlib import Path

import pytest

from swaglabs.findings import load_register
from swaglabs.personas import Persona
from swaglabs.requirements import Requirement, area_tags, load_registry, requirement_tags, tag_problems

REGISTRY = {
    "REQ-A": Requirement("REQ-A", "a", "high"),
    "REQ-B": Requirement("REQ-B", "b", "low"),
}
AREAS = {"sorting": "..."}


def test_a_complete_scenario_has_no_problems() -> None:
    assert tag_problems({"REQ-A", "REQ-B", "risk-high", "smoke", "area-sorting"}, REGISTRY, AREAS) == []


@pytest.mark.parametrize(
    ("tags", "problem"),
    [
        ({"risk-high", "smoke"}, "no @REQ-xx tag"),
        ({"REQ-X", "risk-high", "smoke"}, "unknown requirement"),
        ({"REQ-A", "risk-high", "smoke", "area-nope"}, "unknown area"),
        ({"REQ-A", "smoke"}, "exactly one @risk-*"),
        ({"REQ-A", "risk-high", "risk-low", "smoke"}, "exactly one @risk-*"),
        ({"REQ-A", "REQ-B", "risk-low", "smoke"}, "registry says high"),
        ({"REQ-A", "risk-high"}, "@smoke/@regression"),
        ({"REQ-A", "risk-high", "smoke", "regression"}, "@smoke/@regression"),
    ],
)
def test_broken_rules_are_named(tags: set[str], problem: str) -> None:
    problems = tag_problems(tags, REGISTRY, AREAS)
    assert any(problem in p for p in problems), problems


def test_manual_scenarios_need_no_risk_or_suite() -> None:
    assert tag_problems({"REQ-A", "manual"}, REGISTRY, AREAS) == []


def test_tag_helpers() -> None:
    tags = {"REQ-B", "REQ-A", "area-x", "smoke"}
    assert requirement_tags(tags) == ["REQ-A", "REQ-B"]
    assert area_tags(tags) == ["x"]


def test_registry_loader(tmp_path: Path) -> None:
    path = tmp_path / "r.toml"
    path.write_text('[REQ-1]\ntitle = "t"\nrisk = "medium"\n', encoding="utf-8")
    assert load_registry(path)["REQ-1"].risk == "medium"
    path.write_text('[REQ-1]\ntitle = "t"\nrisk = "extreme"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown risk"):
        load_registry(path)
    path.write_text('[R-1]\ntitle = "t"\nrisk = "low"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="start with"):
        load_registry(path)


GOOD_FINDING = """
[areas]
sorting = "sorting works"

[SL-01]
title = "t"
personas = ["problem_user"]
area = "sorting"
requirement = "REQ-A"
severity = "major"
"""


def test_findings_loader_accepts_a_valid_register(tmp_path: Path) -> None:
    path = tmp_path / "f.toml"
    path.write_text(GOOD_FINDING, encoding="utf-8")
    register = load_register(path, REGISTRY)
    assert register.findings[0].personas == frozenset({Persona.PROBLEM})


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('personas = ["problem_user"]', 'personas = ["locked_out_user"]', "non-runnable persona"),
        ('personas = ["problem_user"]', "personas = []", "non-empty personas"),
        ('area = "sorting"', 'area = "nope"', "not declared"),
        ('requirement = "REQ-A"', 'requirement = "REQ-Z"', "not in requirements.toml"),
        ('severity = "major"', 'severity = "huge"', "severity must be"),
        ('title = "t"', 'title = ""', "needs a title"),
        ("[SL-01]", "[BUG-01]", "start with 'SL-'"),
    ],
)
def test_findings_loader_refuses_broken_entries(tmp_path: Path, old: str, new: str, message: str) -> None:
    path = tmp_path / "f.toml"
    path.write_text(GOOD_FINDING.replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_register(path, REGISTRY)


def test_personas() -> None:
    assert Persona.LOCKED_OUT not in Persona.runnable()
    assert Persona.parse("visual_user") is Persona.VISUAL
    with pytest.raises(ValueError, match="unknown persona"):
        Persona.parse("admin")
