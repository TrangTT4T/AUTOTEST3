"""What the tests read from the order-events system, as typed values (parsed from its JSON)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class SandboxInfo:
    """The system's published timings. The consistency target is a requirement (REQ-13)."""

    build: str
    consistency_target: float
    visibility_timeout: float
    retry_base: float
    retry_factor: float
    max_attempts: int
    gateway_timeout: float

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SandboxInfo:
        t = data["timings"]
        return cls(
            build=data["build"],
            consistency_target=float(t["consistency_target"]),
            visibility_timeout=float(t["visibility_timeout"]),
            retry_base=float(t["retry_base"]),
            retry_factor=float(t["retry_factor"]),
            max_attempts=int(t["max_attempts"]),
            gateway_timeout=float(t["gateway_timeout"]),
        )

    def backoff(self, attempt: int) -> float:
        """Documented delay before the attempt that follows ``attempt``."""
        return self.retry_base * self.retry_factor ** (attempt - 1)

    @property
    def quiet_period(self) -> float:
        """No activity for this long means no redelivery or retry can still be pending."""
        return self.visibility_timeout + self.backoff(self.max_attempts - 1)

    @property
    def retry_budget(self) -> float:
        """Longest time a message can spend failing before it reaches the dead-letter queue."""
        waits = sum(self.backoff(a) for a in range(1, self.max_attempts))
        return waits + self.max_attempts * self.gateway_timeout


@dataclass(frozen=True)
class Item:
    sku: str
    quantity: int
    unit_price: Decimal

    def to_json(self) -> dict[str, Any]:
        return {"sku": self.sku, "quantity": self.quantity, "unit_price": str(self.unit_price)}


@dataclass(frozen=True)
class Delivery:
    """One delivery of one event to one subscription, and what the consumer did with it."""

    at: float
    subscription: str
    event_id: str
    type: str
    sequence: int
    delivery: int
    reason: str
    result: str
    detail: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Delivery:
        return cls(**{k: data[k] for k in cls.__dataclass_fields__})

    def describe(self) -> str:
        detail = f" ({self.detail})" if self.detail else ""
        return (
            f"{self.at:7.3f}s {self.subscription:<10} {self.type:<12} seq {self.sequence} "
            f"#{self.delivery} {self.reason:<20} -> {self.result}{detail}"
        )


@dataclass(frozen=True)
class Charge:
    charge_id: str
    idempotency_key: str
    order_id: str
    amount: Decimal
    at: float

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Charge:
        return cls(
            data["charge_id"], data["idempotency_key"], data["order_id"], Decimal(data["amount"]), data["at"]
        )


@dataclass(frozen=True)
class DeadLetter:
    subscription: str
    event_id: str
    type: str
    attempts: int
    error: str
    at: float

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> DeadLetter:
        event = data["event"]
        return cls(
            data["subscription"],
            event["event_id"],
            event["type"],
            data["attempts"],
            data["error"],
            data["at"],
        )


@dataclass(frozen=True)
class OrderView:
    """The read model: what the order screen shows."""

    order_id: str
    status: str
    version: int
    history: tuple[str, ...]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> OrderView:
        return cls(data["order_id"], data["status"], int(data["version"]), tuple(data["history"]))


@dataclass(frozen=True)
class Frame:
    """One live status update, with the moment this test received it (its own clock)."""

    frame: int
    order_id: str
    status: str
    sequence: int
    event_id: str
    received_at: float

    @classmethod
    def from_json(cls, data: dict[str, Any], received_at: float) -> Frame:
        return cls(
            data["frame"], data["order_id"], data["status"], data["sequence"], data["event_id"], received_at
        )


@dataclass(frozen=True)
class Fault:
    """A fault to inject into one flow. The correlation id is added when it is sent."""

    kind: str
    subscription: str | None = None
    event_type: str | None = None
    times: int = 1
    seconds: float = 0.0
    after_type: str | None = None
    after_status: str | None = None

    @classmethod
    def duplicate(cls, subscription: str, event_type: str) -> Fault:
        return cls("duplicate", subscription, event_type)

    @classmethod
    def lose_ack(cls, subscription: str, event_type: str) -> Fault:
        return cls("lose_ack", subscription, event_type)

    @classmethod
    def deliver_after(cls, subscription: str, event_type: str, after_type: str) -> Fault:
        return cls("deliver_after", subscription, event_type, after_type=after_type)

    @classmethod
    def delay(cls, subscription: str, event_type: str, seconds: float) -> Fault:
        return cls("delay", subscription, event_type, seconds=seconds)

    @classmethod
    def gateway_fail(cls, times: int = 1) -> Fault:
        return cls("gateway_fail", times=times)

    @classmethod
    def gateway_slow(cls, seconds: float) -> Fault:
        return cls("gateway_slow", seconds=seconds)

    @classmethod
    def drop_connection(cls, after_status: str) -> Fault:
        return cls("drop_connection", after_status=after_status)

    def to_json(self, correlation_id: str) -> dict[str, Any]:
        data = {k: v for k, v in asdict(self).items() if v is not None}
        if self.times == 1:
            data.pop("times")
        if not self.seconds:
            data.pop("seconds")
        return {**data, "correlation_id": correlation_id}

    def describe(self) -> str:
        parts = [self.kind]
        if self.event_type:
            parts.append(self.event_type)
        if self.subscription:
            parts.append(f"-> {self.subscription}")
        if self.after_type:
            parts.append(f"after {self.after_type}")
        if self.after_status:
            parts.append(f"after '{self.after_status}'")
        if self.seconds:
            parts.append(f"{self.seconds:g}s")
        if self.times > 1:
            parts.append(f"x{self.times}")
        return " ".join(parts)
