"""Known defects found in this lab (Day 4 format), and the builds they are present in.

A test that detects one is marked ``@pytest.mark.known_defect("D-12-01")`` (BDD: tag
``@defect-D-12-01``). When the build under test contains the defect, the test becomes a
strict xfail limited to ``AssertionError``: it must still fail for the documented reason,
and it turns red (XPASS) the day the defect disappears without the register being updated.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    id: str
    title: str
    severity: str
    requirement: str
    present_in: frozenset[str]
    detected_by: str


FINDINGS: dict[str, Finding] = {
    f.id: f
    for f in (
        Finding(
            "D-12-01",
            "A payment retried after a gateway timeout charges the customer twice",
            "Critical",
            "REQ-10",
            frozenset({"release"}),
            "tests/events/test_exactly_once.py::test_payment_retried_after_gateway_timeout_charges_once",
        ),
        Finding(
            "D-12-02",
            "A late 'packed' update overwrites 'shipped': the order status goes backwards",
            "High",
            "REQ-11",
            frozenset({"release"}),
            "tests/events/test_ordering.py::test_late_packed_update_does_not_undo_shipped",
        ),
        Finding(
            "D-12-03",
            "After a reconnect, the live status skips one update",
            "Medium",
            "REQ-13",
            frozenset({"release"}),
            "tests/events/test_live_status.py::test_status_stream_catches_up_after_a_reconnect",
        ),
    )
}


def active(defect_id: str, build: str) -> Finding | None:
    """The finding if it is present in ``build``; KeyError for an unregistered id (a typo)."""
    finding = FINDINGS[defect_id]
    return finding if build in finding.present_in else None
