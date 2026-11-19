"""REQ-10 · Each order is charged and processed exactly once: duplicates, lost acks, resubmits, timeouts."""

import pytest

from framework.events.flow import OrderFlow
from framework.events.model import Fault
from framework.requirements_marks import covers
from framework.waiting import holds_for

pytestmark = [pytest.mark.events, pytest.mark.p1]


@covers("REQ-10")
def test_duplicate_payment_message_charges_once(flow: OrderFlow) -> None:
    """Payment message delivered twice: one charge; the copy is recorded as ignored."""
    flow.inject(Fault.duplicate("payments", "OrderPlaced"))
    flow.place()
    flow.wait_for_status("shipped")

    payments = flow.wait_for_deliveries("payments", "OrderPlaced", count=2)
    assert [(d.reason, d.result) for d in payments] == [
        ("first", "applied"),
        ("duplicate", "ignored: duplicate"),
    ], [d.describe() for d in payments]
    assert len(flow.charges()) == 1, flow.charges()


@covers("REQ-10")
def test_lost_acknowledgement_does_not_charge_twice(flow: OrderFlow) -> None:
    """Ack lost after a successful payment: redelivered after the visibility timeout; still one charge."""
    flow.inject(Fault.lose_ack("payments", "OrderPlaced"))
    flow.place()
    flow.wait_for_status("shipped")

    first, again = flow.wait_for_deliveries("payments", "OrderPlaced", count=2)
    assert (first.result, first.detail) == ("applied", "acknowledgement lost"), first.describe()
    assert (again.reason, again.result) == ("redelivery (no ack)", "ignored: duplicate"), again.describe()
    assert again.at - first.at >= flow.info.visibility_timeout * 0.9, (
        "redelivered before the visibility timeout"
    )
    assert len(flow.charges()) == 1, flow.charges()


@covers("REQ-10")
def test_resubmitted_order_creates_one_order(flow: OrderFlow) -> None:
    """The app sends the same order twice (same idempotency key): one order, one charge."""
    first = flow.place()
    second = flow.place()  # same idempotency key: a retry after a lost HTTP response
    flow.wait_for_status("shipped")

    assert second == first
    assert len(flow.published("OrderPlaced")) == 1
    assert len(flow.charges()) == 1, flow.charges()


@covers("REQ-10")
@pytest.mark.known_defect("D-12-01")
def test_payment_retried_after_gateway_timeout_charges_once(flow: OrderFlow) -> None:
    """Gateway answers after the worker gave up and retried: the late answer must not add a charge."""
    late = flow.info.gateway_timeout + 0.3
    flow.inject(Fault.gateway_slow(seconds=late))
    flow.place()
    flow.wait_for_status("shipped", timeout=flow.info.consistency_target + flow.info.retry_budget)

    payments = flow.deliveries("payments", "OrderPlaced")
    assert [d.result for d in payments] == ["failed", "applied"], [d.describe() for d in payments]
    assert "timeout" in payments[0].detail
    # The first call is still running inside the gateway; watch until its answer has surely arrived.
    charges = holds_for(flow.charges, lambda c: len(c) <= 1, duration=late)
    assert len(charges) == 1, charges
