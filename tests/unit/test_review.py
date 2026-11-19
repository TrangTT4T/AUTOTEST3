"""The review tool must catch the problems it was built for, including the real one from Day 4."""

from pathlib import Path

from framework.review import (
    ScenarioInfo,
    StepDef,
    StepUse,
    definition_smells,
    main,
    near_duplicates,
    review,
    scenario_smells,
    scenarios_in,
    step_definitions,
)

STEPS_SOURCE = """
from pytest_bdd import given, then, when, parsers
from framework.step_types import parsed

@given("a visitor with an empty cart")
def empty(): ...

@then(parsed('the cart contains {quantity:d} "{name:Quoted}"'))
def contains(): ...

@then(parsed('the cart contains {quantity:d} "{name:Quoted}" in variant "{variant:Quoted}"'))
def contains_variant(): ...

@then(parsers.parse('the old style "{name}"'))
def old_style(): ...
"""


def _use(keyword: str, text: str) -> StepUse:
    return StepUse(keyword, text, "f.feature:1")


def _scenario(*steps: StepUse, tags: frozenset[str] = frozenset()) -> ScenarioInfo:
    return ScenarioInfo("S", "f.feature:1", tuple(steps), 1, tags)


def test_step_definitions_are_read_from_decorators() -> None:
    defs = step_definitions(STEPS_SOURCE, "steps.py")
    assert [(d.keyword, d.kind, d.function) for d in defs] == [
        ("given", "exact", "empty"),
        ("then", "parse", "contains"),
        ("then", "parse", "contains_variant"),
        ("then", "parse", "old_style"),
    ]


def test_quoted_placeholders_no_longer_clash() -> None:
    """Regression test for the Day 4 finding: "{name}" swallowed '... in variant "L / Red'."""
    defs = step_definitions(STEPS_SOURCE, "steps.py")[:3]
    result = review(defs, [_scenario(_use("then", 'the cart contains 1 "Noir jacket" in variant "L / Red"'))])
    assert result.ambiguous == []
    assert result.usage[defs[2]] == 1


def test_greedy_placeholder_is_ambiguous_and_reported() -> None:
    greedy = StepDef("then", 'the cart contains {quantity:d} "{name}"', "parse", "f", "s.py:1")
    variant = StepDef(
        "then", 'the cart contains {quantity:d} "{name}" in variant "{v}"', "parse", "g", "s.py:2"
    )
    result = review([greedy, variant], [_scenario(_use("then", 'the cart contains 1 "A" in variant "B"'))])
    assert len(result.ambiguous) == 1
    assert {rule for rule, _, _ in result.smells} == {"greedy-placeholder"}


def test_undefined_and_unused_steps() -> None:
    defs = step_definitions(STEPS_SOURCE, "steps.py")[:1]
    result = review(defs, [_scenario(_use("when", "something nobody wrote"))])
    assert [u.text for u in result.undefined] == ["something nobody wrote"]
    assert result.unused == defs


def test_manual_scenarios_are_not_undefined() -> None:
    # Manual scenarios are still specifications: Gherkin rules (e.g. a Then) still apply.
    steps = (_use("given", "not automated"), _use("then", "checked by hand"))
    manual = _scenario(*steps, tags=frozenset({"manual"}))
    result = review([], [manual])
    assert result.undefined == []
    assert len(result.manual_steps) == 2
    assert result.problem_count == 0


def test_scenario_smells() -> None:
    imperative = _scenario(_use("when", "they click the Add button"), _use("then", "the total is £55.00"))
    assert {rule for rule, _, _ in scenario_smells(imperative)} == {"imperative", "hard-coded-money"}
    two_whens = _scenario(_use("when", "a"), _use("when", "b"))
    assert {rule for rule, _, _ in scenario_smells(two_whens)} == {"several-whens", "no-then"}


def test_near_duplicates_are_candidates_not_problems() -> None:
    a = StepDef("when", "they add the product to the cart", "exact", "f", "s.py:1")
    b = StepDef("when", "they add the products to the cart", "exact", "g", "s.py:2")
    assert near_duplicates([a, b])
    result = review([a, b], [_scenario(_use("when", a.pattern), _use("then", "x"))])
    assert result.near_duplicates
    assert result.problem_count == len(result.undefined) + len(result.unused)


def test_outline_steps_use_the_first_example_row() -> None:
    feature = (
        "@web\nFeature: F\n  Scenario Outline: O\n    When they add <n> items\n"
        "    Then done\n\n    Examples:\n      | n |\n      | 2 |\n      | 3 |\n"
    )
    [scenario] = scenarios_in(feature, "f.feature")
    assert scenario.examples == 2
    assert scenario.steps[0].text == "they add 2 items"
    assert "web" in scenario.tags


def test_definition_smells_ignore_typed_placeholders() -> None:
    typed = StepDef("then", 'x "{a:Quoted}"', "parse", "f", "s.py:1")
    assert definition_smells([typed]) == []


def _project(root: Path, feature: str, steps: str) -> Path:
    """A minimal project layout for the review CLI: features, steps, requirement registry."""
    (root / "features").mkdir(parents=True)
    (root / "tests" / "steps").mkdir(parents=True)
    (root / "features" / "f.feature").write_text(feature, encoding="utf-8")
    (root / "tests" / "steps" / "s.py").write_text(steps, encoding="utf-8")
    (root / "requirements.toml").write_text('[REQ-01]\ntitle = "t"\nrisk = "low"\n', encoding="utf-8")
    return root


CLEAN_FEATURE = (
    "@web\nFeature: F\n  @REQ-01 @risk-low @smoke\n  Scenario: S\n    Given a thing\n    Then it works\n"
)
CLEAN_STEPS = (
    "from pytest_bdd import given, then\n"
    "@given('a thing')\ndef a() -> None: ...\n"
    "@then('it works')\ndef b() -> None: ...\n"
)


def test_cli_passes_a_clean_project_and_writes_the_report(tmp_path: Path) -> None:
    root = _project(tmp_path, CLEAN_FEATURE, CLEAN_STEPS)
    assert main(["--root", str(root), "--strict"]) == 0
    report = (root / "reports" / "bdd-review.md").read_text(encoding="utf-8")
    assert "| then | `it works` | 1 | tests/steps/s.py:5 |" in report


def test_cli_strict_fails_on_an_undefined_step(tmp_path: Path) -> None:
    root = _project(tmp_path, CLEAN_FEATURE.replace("it works", "it explodes"), CLEAN_STEPS)
    assert main(["--root", str(root)]) == 0  # report only
    assert main(["--root", str(root), "--strict"]) == 1
    assert "it explodes" in (root / "reports" / "bdd-review.md").read_text(encoding="utf-8")
