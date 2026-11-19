"""Fault injection, scoped by correlation id so that parallel tests never see each other's faults."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from sandbox.model import new_id

KINDS: dict[str, str] = {
    "duplicate": "deliver the message twice to the subscription",
    "lose_ack": "process the message, then lose the acknowledgement (the broker redelivers it)",
    "deliver_after": "hold the message until `after_type` has been delivered to the same subscription",
    "delay": "wait `seconds` before delivering the message",
    "gateway_fail": "the payment gateway answers 503 Service Unavailable",
    "gateway_slow": "the payment gateway answers after `seconds`",
    "drop_connection": "close the customer's WebSocket right after the frame with `after_status`",
}


class FaultError(ValueError):
    """A fault request the sandbox cannot apply."""


@dataclass
class Fault:
    kind: str
    correlation_id: str
    subscription: str | None = None
    event_type: str | None = None
    times: int = 1
    seconds: float = 0.0
    after_type: str | None = None
    after_status: str | None = None
    fault_id: str = field(default_factory=lambda: new_id("f"))
    used: int = 0

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Fault:
        allowed = {f.name for f in fields(cls)} - {"fault_id", "used"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise FaultError(f"unknown fault fields {unknown}; allowed: {sorted(allowed)}")
        if data.get("kind") not in KINDS:
            raise FaultError(f"unknown fault kind {data.get('kind')!r}; kinds: {sorted(KINDS)}")
        if not data.get("correlation_id"):
            raise FaultError("correlation_id is required: faults are scoped to one flow")
        fault = cls(**data)
        if fault.times < 1 or fault.seconds < 0:
            raise FaultError("times must be >= 1 and seconds >= 0")
        if fault.kind == "deliver_after" and not fault.after_type:
            raise FaultError("deliver_after needs after_type")
        if fault.kind == "drop_connection" and not fault.after_status:
            raise FaultError("drop_connection needs after_status")
        return fault

    def matches(
        self,
        kind: str,
        correlation_id: str,
        subscription: str | None,
        event_type: str | None,
        status: str | None,
    ) -> bool:
        return (
            self.kind == kind
            and self.used < self.times
            and self.correlation_id == correlation_id
            and self.subscription in (None, subscription)
            and self.event_type in (None, event_type)
            and self.after_status in (None, status)
        )


class Faults:
    def __init__(self) -> None:
        self._faults: list[Fault] = []

    def add(self, fault: Fault) -> Fault:
        self._faults.append(fault)
        return fault

    def take(
        self,
        kind: str,
        correlation_id: str,
        subscription: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
    ) -> Fault | None:
        """The first matching fault with uses left, which is then used once; or None."""
        for fault in self._faults:
            if fault.matches(kind, correlation_id, subscription, event_type, status):
                fault.used += 1
                return fault
        return None
