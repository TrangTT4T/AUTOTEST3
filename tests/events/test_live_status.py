"""REQ-13 · Each status change reaches the customer within the target, also after a reconnect or outage."""

import time

import pytest

from framework.events.flow import OrderFlow
from framework.events.model import Fault
from framework.requirements_marks import covers
from framework.waiting import holds_for

pytestmark = [pytest.mark.events, pytest.mark.p1]
ALL_STATUSES = ["placed", "paid", "packed", "shipped"]


@covers("REQ-13")
def test_every_status_reaches_the_customer_within_the_target(flow: OrderFlow) -> None:
    """No faults: placed, paid, packed, shipped arrive in order, the last within the consistency target."""
    flow.place()
    flow.wait_for_status("shipped")

    assert flow.statuses() == ALL_STATUSES
    assert flow.converged_in is not None
    assert flow.converged_in <= flow.info.consistency_target


@covers("REQ-13")
@pytest.mark.known_defect("D-12-03")
def test_status_stream_catches_up_after_a_reconnect(flow: OrderFlow) -> None:
    """Connection lost after 'paid'; the updates sent meanwhile arrive after reconnecting, none missing."""
    flow.inject(Fault.drop_connection(after_status="paid"))
    flow.place()
    flow.stream.wait_disconnected(timeout=flow.info.consistency_target)
    flow.wait_for_view_status("shipped")  # the system moved on while the customer was offline

    reconnected_at = time.monotonic()
    flow.stream.reconnect()
    flow.wait_for_status("shipped", measured_from=reconnected_at)
    assert flow.statuses() == ALL_STATUSES


@covers("REQ-13", "REQ-10")
def test_order_completes_once_after_a_worker_outage(flow: OrderFlow) -> None:
    """Fulfilment down: the order waits at 'paid', nothing is lost; after the restart it completes once.

    Stops a worker for the whole sandbox: safe because each pytest worker has its own sandbox.
    """
    flow.client.stop_worker("fulfilment")
    try:
        flow.place()
        flow.wait_for_status("paid")
        holds_for(flow.statuses, lambda s: s[-1] == "paid", duration=0.5)
        restarted_at = time.monotonic()
    finally:
        flow.client.start_worker("fulfilment")
    flow.wait_for_status("shipped", measured_from=restarted_at)

    assert flow.statuses() == ALL_STATUSES
    fulfilment = flow.deliveries("fulfilment", "OrderPaid")
    assert [d.result for d in fulfilment] == ["applied"], [d.describe() for d in fulfilment]
    assert len(flow.charges()) == 1
