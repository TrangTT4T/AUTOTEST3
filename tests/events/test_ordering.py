"""REQ-11 · The order status never goes backwards: late and repeated updates."""

from collections.abc import Callable

import pytest

from framework.events import oracles
from framework.events.flow import OrderFlow
from framework.events.model import Fault
from framework.requirements_marks import covers

pytestmark = [pytest.mark.events, pytest.mark.p1]
ALL_STATUSES = ["placed", "paid", "packed", "shipped"]


@covers("REQ-11")
@pytest.mark.known_defect("D-12-02")
def test_late_packed_update_does_not_undo_shipped(flow: OrderFlow) -> None:
    """'packed' reaches the read model after 'shipped': what the customer sees never goes backwards."""
    flow.inject(Fault.deliver_after("projector", "OrderPacked", after_type="OrderShipped"))
    flow.place()
    flow.wait_for_status("shipped")
    flow.wait_for_deliveries("projector", "OrderPacked", 1, where=lambda d: d.reason.startswith("released"))

    seen = flow.statuses()
    assert oracles.backwards(seen) == [], f"the customer saw {seen}"
    view = flow.view()
    assert view is not None
    assert view.status == "shipped", view
    assert oracles.backwards(view.history) == [], view.history


@covers("REQ-11")
def test_repeated_updates_are_shown_once(flow: OrderFlow) -> None:
    """Every event delivered twice to the read model: each status is shown once, in order."""
    for event_type in ("OrderPlaced", "OrderPaid", "OrderPacked", "OrderShipped"):
        flow.inject(Fault.duplicate("projector", event_type))
    flow.place()
    flow.wait_for_status("shipped")
    flow.wait_for_deliveries("projector", "OrderShipped", count=2)

    assert flow.statuses() == ALL_STATUSES
    assert len(oracles.redelivered(flow.deliveries("projector"))) == 4


@covers("REQ-11", "REQ-10")
def test_a_disturbed_order_does_not_disturb_another(
    flow: OrderFlow, flow_factory: Callable[[str], OrderFlow]
) -> None:
    """Two customers at once, faults on one only: each sees only its own, complete, ordered statuses."""
    calm = flow_factory("calm")
    flow.inject(Fault.duplicate("payments", "OrderPlaced"))
    flow.inject(Fault.delay("projector", "OrderPaid", seconds=0.3))
    flow.place()
    calm.place()
    flow.wait_for_status("shipped")
    calm.wait_for_status("shipped")

    assert calm.statuses() == ALL_STATUSES
    assert flow.statuses() == ALL_STATUSES
    assert {f.order_id for f in calm.stream.frames} == {calm.order_id}
    assert len(flow.charges()) == len(calm.charges()) == 1
    assert calm.deliveries("payments")
    assert all(d.reason == "first" for d in calm.deliveries())
