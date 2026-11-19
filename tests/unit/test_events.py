"""Unit tests for the asynchronous-system test framework (framework/events), no sandbox needed."""

import ast
import re
from decimal import Decimal
from pathlib import Path

import pytest

from framework.events import oracles
from framework.events.correlation import correlation_id
from framework.events.findings import FINDINGS, Finding, active
from framework.events.model import Delivery, Fault, Item, SandboxInfo
from framework.plugins.selection import deselect_reason
from framework.waiting import holds_for, wait_until, wait_until_stable

ROOT = Path(__file__).resolve().parents[2]
INFO = SandboxInfo("release", 2.0, 0.6, 0.2, 2.0, 3, 0.5)


def _delivery(at: float, number: int, reason: str = "first", result: str = "applied") -> Delivery:
    return Delivery(at, "payments", "e-1", "OrderPlaced", 1, number, reason, result, "")


# --- oracles -----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["placed", "paid", "packed", "shipped"], []),
        (["placed", "paid", "shipped"], []),  # skipping a status is not going backwards
        (["placed", "paid", "shipped", "packed"], ["shipped -> packed"]),
        (["paid", "placed", "paid"], ["paid -> placed"]),
    ],
)
def test_backwards_finds_every_step_back(statuses: list[str], expected: list[str]) -> None:
    assert oracles.backwards(statuses) == expected


def test_repeated_and_redelivered() -> None:
    assert oracles.repeated(["placed", "paid", "paid"]) == ["paid"]
    deliveries = [_delivery(0.1, 1), _delivery(0.2, 2, "duplicate", "ignored: duplicate")]
    assert oracles.redelivered(deliveries) == {"payments OrderPlaced e-1": 2}


def test_gaps_and_attempts() -> None:
    deliveries = [_delivery(0.0, 1), _delivery(0.2, 2, "retry"), _delivery(0.61, 3, "retry")]
    assert oracles.gaps(deliveries) == [0.2, 0.41]
    assert oracles.max_attempt(deliveries) == 3
    assert oracles.max_attempt([]) == 0


# --- model -------------------------------------------------------------------------
def test_backoff_and_retry_budget_follow_the_published_timings() -> None:
    assert [INFO.backoff(a) for a in (1, 2)] == [0.2, 0.4]
    assert INFO.retry_budget == pytest.approx(0.2 + 0.4 + 3 * 0.5)
    assert INFO.quiet_period == pytest.approx(0.6 + 0.4)


def test_fault_json_is_scoped_to_the_flow() -> None:
    assert Fault.duplicate("payments", "OrderPlaced").to_json("T-1") == {
        "kind": "duplicate",
        "subscription": "payments",
        "event_type": "OrderPlaced",
        "correlation_id": "T-1",
    }
    assert Fault.gateway_fail(times=3).to_json("T-1") == {
        "kind": "gateway_fail",
        "times": 3,
        "correlation_id": "T-1",
    }
    assert Fault.deliver_after("projector", "OrderPacked", "OrderShipped").describe() == (
        "deliver_after OrderPacked -> projector after OrderShipped"
    )


def test_items_are_sent_as_decimal_strings() -> None:
    assert Item("SKU", 2, Decimal("29.99")).to_json() == {"sku": "SKU", "quantity": 2, "unit_price": "29.99"}


# --- correlation ids ------------------------------------------------------------------
def test_correlation_ids_are_readable_and_unique() -> None:
    a = correlation_id("4f1c2a9b", "gw0", "tests/events/test_x.py::test_duplicate_payment[1]")
    b = correlation_id("4f1c2a9b", "gw0", "tests/events/test_y.py::test_duplicate_payment[1]")
    assert re.fullmatch(r"T-4f1c2a-gw0-test-duplicate-payment-1-[0-9a-f]{4}", a), a
    assert a != b  # same test name in two modules
    assert correlation_id("4f1c2a9b", "gw0", "t.py::t", "Calm one").endswith("-calm-one")


# --- waiting helpers --------------------------------------------------------------------
def test_wait_until_reports_the_last_value() -> None:
    values = iter(["pending", "pending", "shipped"])
    assert wait_until(lambda: next(values), lambda v: v == "shipped", timeout=1, interval=0.001) == "shipped"
    with pytest.raises(TimeoutError, match="last value: 'pending'"):
        wait_until(lambda: "pending", lambda v: v == "shipped", timeout=0.05, interval=0.01)


def test_holds_for_fails_at_the_first_violation() -> None:
    values = iter([1, 1, 2, 2])
    with pytest.raises(AssertionError, match=r"condition broken .*: 2"):
        holds_for(lambda: next(values), lambda n: n <= 1, duration=1, interval=0.001)
    assert holds_for(lambda: 1, lambda n: n <= 1, duration=0.02, interval=0.005) == 1


def test_wait_until_stable_waits_for_the_last_change() -> None:
    values = iter([1, 1, 2, 2, 2, 2, 2, 2, 2, 2])
    assert wait_until_stable(lambda: next(values), quiet=0.02, timeout=1, interval=0.005) == 2
    counter = iter(range(1000))
    with pytest.raises(TimeoutError, match="still changing"):
        wait_until_stable(lambda: next(counter), quiet=0.05, timeout=0.1, interval=0.005)


# --- platform selection -------------------------------------------------------------------
@pytest.mark.parametrize(
    ("store", "folder", "platforms", "runs"),
    [
        ("fake", "events", set(), True),
        ("web", "events", set(), False),
        ("mobile", "events", set(), False),
        ("fake", "tests", {"events"}, True),
        ("web", "tests", {"events"}, False),
        ("fake", "tests", {"mobile"}, True),
        ("web", "tests", {"web"}, True),
        ("mobile", "tests", {"web"}, False),
        ("mobile", "mobile", set(), True),
        ("fake", "e2e", set(), False),
        ("web", "unit", set(), True),
    ],
)
def test_platform_selection(store: str, folder: str, platforms: set[str], runs: bool) -> None:
    assert (deselect_reason(store, folder, platforms) is None) == runs


# --- known-defect register ---------------------------------------------------------------
def _defect_ids_used() -> set[str]:
    used = set()
    for path in (ROOT / "tests").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "known_defect"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                used.add(str(node.args[0].value))
    for path in (ROOT / "features").rglob("*.feature"):
        used |= set(re.findall(r"@defect-(D-[\w-]+)", path.read_text(encoding="utf-8")))
    return used


def test_every_known_defect_mark_is_registered_and_every_finding_is_tested() -> None:
    used = _defect_ids_used()
    assert used <= set(FINDINGS), f"unregistered defect ids: {sorted(used - set(FINDINGS))}"
    assert set(FINDINGS) <= used, f"findings no test detects: {sorted(set(FINDINGS) - used)}"


@pytest.mark.parametrize("finding", FINDINGS.values(), ids=lambda f: f.id)
def test_each_finding_names_a_real_test(finding: Finding) -> None:
    path, name = finding.detected_by.split("::")
    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), finding.detected_by


def test_findings_apply_only_to_their_builds() -> None:
    assert active("D-12-01", "release") is not None
    assert active("D-12-01", "fixed") is None
    with pytest.raises(KeyError):
        active("D-99-99", "release")
