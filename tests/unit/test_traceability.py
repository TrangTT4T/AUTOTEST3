from pathlib import Path

import pytest

from framework.requirements import Requirement
from framework.traceability import build_matrix, declared_scenarios, status_of, to_markdown

REGISTRY = {
    "REQ-01": Requirement("REQ-01", "Search", "medium"),
    "REQ-02": Requirement("REQ-02", "Product page", "medium"),
    "REQ-03": Requirement("REQ-03", "Add to cart", "high"),
}


@pytest.mark.parametrize(
    ("declared", "outcomes", "status"),
    [
        (0, {}, "NOT COVERED"),
        (2, {"passed": 1, "failed": 1}, "FAIL"),
        (2, {"passed": 1, "blocked": 1}, "BLOCKED"),
        (2, {"passed": 1, "known-defect": 1}, "KNOWN DEFECT"),
        (2, {"known-defect": 1, "blocked": 1}, "KNOWN DEFECT"),
        (2, {"known-defect": 1, "failed": 1}, "FAIL"),
        (1, {"passed": 1}, "PASS"),
        (1, {"skipped": 1}, "MANUAL"),
        (1, {}, "NOT RUN"),
    ],
)
def test_status(declared: int, outcomes: dict[str, int], status: str) -> None:
    full = {"passed": 0, "failed": 0, "known-defect": 0, "blocked": 0, "skipped": 0, **outcomes}
    assert status_of(declared, full) == status


def test_matrix_lists_every_registered_requirement() -> None:
    declared = {"REQ-01": ["a"], "REQ-03": ["b", "c"]}
    results = [(["REQ-01"], "passed"), (["REQ-03"], "passed"), (["REQ-03"], "blocked")]
    rows = {row.requirement.id: row for row in build_matrix(REGISTRY, declared, results)}
    assert rows["REQ-01"].status == "PASS"
    assert rows["REQ-02"].status == "NOT COVERED"
    assert rows["REQ-03"].status == "BLOCKED"
    assert rows["REQ-03"].declared == 2


def test_declared_scenarios_reads_feature_tags(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        "@web @REQ-01\nFeature: F\n  Rule: R\n    @REQ-02\n    Scenario: S1\n      Given x\n"
        "  Scenario: S2\n    Given y\n",
        encoding="utf-8",
    )
    declared = declared_scenarios(tmp_path)
    assert declared == {"REQ-01": ["a.feature: S1", "a.feature: S2"], "REQ-02": ["a.feature: S1"]}


def test_markdown_has_a_row_per_requirement() -> None:
    md = to_markdown(build_matrix(REGISTRY, {}, []))
    assert md.count("NOT COVERED") == 3
