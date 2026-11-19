"""REQ-12 · Failing messages are retried with backoff, then dead-lettered; parked messages can be redriven."""

import time
from collections.abc import Callable

import pytest

from framework.events import oracles
from framework.events.flow import OrderFlow
from framework.events.model import Fault
from framework.requirements_marks import covers
from framework.waiting import holds_for

pytestmark = [pytest.mark.events, pytest.mark.p2]


@covers("REQ-12", "REQ-10")
def test_transient_gateway_failure_is_retried_with_backoff(flow: OrderFlow) -> None:
    """Gateway fails twice, then works: 3 attempts, growing gaps, one charge."""
    flow.inject(Fault.gateway_fail(times=2))
    flow.place()
    flow.wait_for_status("shipped", timeout=flow.info.consistency_target + flow.info.retry_budget)

    attempts = flow.deliveries("payments", "OrderPlaced")
    assert [(d.reason, d.result) for d in attempts] == [
        ("first", "failed"),
        ("retry", "failed"),
        ("retry", "applied"),
    ], [d.describe() for d in attempts]
    expected = [flow.info.backoff(1), flow.info.backoff(2)]
    measured = oracles.gaps(attempts)
    assert all(m >= e * 0.9 for m, e in zip(measured, expected, strict=True)), (measured, expected)
    assert len(flow.charges()) == 1, flow.charges()


@covers("REQ-12", "REQ-10")
def test_failing_message_is_dead_lettered_then_redriven(flow: OrderFlow) -> None:
    """Gateway down for every attempt: parked, nothing charged; after the outage, a redrive completes it."""
    flow.inject(Fault.gateway_fail(times=flow.info.max_attempts))
    flow.place()

    (letter,) = flow.wait_for_dead_letters(1)
    assert (letter.type, letter.attempts) == ("OrderPlaced", flow.info.max_attempts), letter
    assert flow.charges() == []
    view = flow.wait_for_view_status("placed")
    holds_for(flow.view, lambda v: v == view, duration=0.3)  # parked, not progressing

    redriven_at = time.monotonic()
    assert flow.client.redrive(flow.correlation_id) == 1
    flow.wait_for_status("shipped", measured_from=redriven_at)
    assert len(flow.charges()) == 1, flow.charges()
    assert flow.dead_letters() == []


@covers("REQ-12")
def test_malformed_message_is_parked_at_once_and_blocks_nothing(
    flow: OrderFlow, flow_factory: Callable[[str], OrderFlow]
) -> None:
    """A malformed message from another producer: parked after 1 attempt; the next order still completes."""
    bad = flow_factory("malformed")
    bad.publish_malformed_order()
    flow.place()
    flow.wait_for_status("shipped")

    (letter,) = bad.wait_for_dead_letters(1)
    assert letter.attempts == 1, "a permanent error must not be retried"
    assert "malformed" in letter.error, letter.error
    assert bad.charges() == []
