"""Order-event steps. Thin: one call on the customer's OrderFlow, then an assertion.

The flow (framework/events) is this system's port: steps never touch HTTP or WebSocket.
"""

from collections.abc import Callable

from pytest_bdd import given, then, when

from framework.events import oracles
from framework.events.flow import OrderFlow
from framework.events.model import Fault
from framework.step_types import parsed

EVENT_OF_STATUS = {
    "placed": "OrderPlaced",
    "paid": "OrderPaid",
    "packed": "OrderPacked",
    "shipped": "OrderShipped",
}
PAYMENT_PROBLEMS = {
    "a duplicate delivery": Fault.duplicate("payments", "OrderPlaced"),
    "a lost acknowledgement": Fault.lose_ack("payments", "OrderPlaced"),
    "a gateway failure": Fault.gateway_fail(times=1),
}


def _statuses(text: str) -> list[str]:
    return [s.strip() for s in text.split(",")]


# --- Given -------------------------------------------------------------------
@given("a customer following their order's status")
def following(flow: OrderFlow) -> None:
    assert flow.stream.connected, "the live status stream is not connected"


@given(parsed('the payment step will suffer "{problem:Quoted}"'))
def payment_problem(flow: OrderFlow, problem: str) -> None:
    assert problem in PAYMENT_PROBLEMS, f"unknown problem {problem!r}; known: {sorted(PAYMENT_PROBLEMS)}"
    flow.inject(PAYMENT_PROBLEMS[problem])


@given(parsed('the "{late:Quoted}" update will reach the order screen after the "{early:Quoted}" update'))
def late_update(flow: OrderFlow, late: str, early: str) -> None:
    flow.inject(Fault.deliver_after("projector", EVENT_OF_STATUS[late], after_type=EVENT_OF_STATUS[early]))


@given("another system has sent a malformed order message", target_fixture="malformed")
def malformed_message(flow_factory: Callable[[str], OrderFlow]) -> OrderFlow:
    bad = flow_factory("malformed")
    bad.publish_malformed_order()
    return bad


@given(parsed('their connection will drop after the "{status:Quoted}" update'))
def connection_drops(flow: OrderFlow, status: str) -> None:
    flow.inject(Fault.drop_connection(after_status=status))


@given("they have placed an order")
def placed_order(flow: OrderFlow) -> None:
    flow.place()


# --- When --------------------------------------------------------------------
@when("they place an order")
def place_order(flow: OrderFlow) -> None:
    flow.place()


@when("they reconnect after the order has shipped")
def reconnect_later(flow: OrderFlow) -> None:
    flow.stream.wait_disconnected(timeout=flow.info.consistency_target)
    flow.wait_for_view_status("shipped")
    flow.stream.reconnect()


# --- Then --------------------------------------------------------------------
@then(parsed('the order is "{status:Quoted}" within the consistency target'))
def status_within_target(flow: OrderFlow, status: str) -> None:
    # retries may legitimately add their budget; the target applies to each status change
    flow.wait_for_status(status, timeout=flow.info.consistency_target + flow.info.retry_budget)


@then("they were charged exactly once")
def charged_once(flow: OrderFlow) -> None:
    flow.settle()  # judge "once" only after every redelivery and retry could have happened
    charges = flow.charges()
    assert len(charges) == 1, f"{len(charges)} charges: {charges}"


@then(parsed('they saw the statuses "{expected:Quoted}" in that order'))
def saw_statuses(flow: OrderFlow, expected: str) -> None:
    wanted = _statuses(expected)
    flow.stream.wait_for(
        lambda frames: bool(frames) and frames[-1].status == wanted[-1],
        flow.info.consistency_target,
        f"status {wanted[-1]!r}",
    )
    assert flow.statuses() == wanted


@then("the status they saw never went backwards")
def never_backwards(flow: OrderFlow) -> None:
    flow.wait_for_deliveries("projector", "OrderPacked", 1, where=lambda d: d.result != "held")
    assert oracles.backwards(flow.statuses()) == [], f"the customer saw {flow.statuses()}"


@then(parsed("the malformed message was parked after {attempts:d} attempt"))
def parked(malformed: OrderFlow, attempts: int) -> None:
    (letter,) = malformed.wait_for_dead_letters(1)
    assert letter.attempts == attempts, letter
