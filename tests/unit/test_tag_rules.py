import pytest

from framework.requirements import Requirement, tag_problems

REGISTRY = {
    "REQ-03": Requirement("REQ-03", "Add to cart", "high"),
    "REQ-04": Requirement("REQ-04", "Cart totals", "high"),
    "REQ-01": Requirement("REQ-01", "Search", "medium"),
    "REQ-08": Requirement("REQ-08", "Accounts", "medium"),
}


def test_valid_scenario_has_no_problems() -> None:
    assert tag_problems({"REQ-03", "REQ-04", "risk-high", "smoke", "web"}, REGISTRY) == []


def test_manual_scenario_needs_no_risk_or_suite() -> None:
    assert tag_problems({"REQ-08", "manual", "web"}, REGISTRY) == []


@pytest.mark.parametrize(
    ("tags", "expected_problem"),
    [
        ({"risk-high", "smoke", "web"}, "no @REQ-xx tag"),
        ({"REQ-99", "risk-high", "smoke", "web"}, "unknown requirement"),
        ({"REQ-01", "risk-high", "regression", "web"}, "registry says medium"),
        ({"REQ-01", "risk-medium", "risk-low", "regression", "web"}, "exactly one @risk-*"),
        ({"REQ-01", "risk-medium", "web"}, "exactly one of @smoke/@regression"),
        ({"REQ-01", "risk-medium", "smoke", "regression", "web"}, "exactly one of @smoke/@regression"),
        ({"REQ-01", "risk-medium", "regression"}, "no platform tag"),
    ],
)
def test_broken_rules_are_reported(tags: set[str], expected_problem: str) -> None:
    problems = tag_problems(tags, REGISTRY)
    assert any(expected_problem in p for p in problems), problems


def test_highest_risk_of_several_requirements_wins() -> None:
    problems = tag_problems({"REQ-01", "REQ-03", "risk-medium", "smoke", "web"}, REGISTRY)
    assert problems == ["@risk-medium but registry says high for ['REQ-01', 'REQ-03']"]
