"""Events and the shared clock."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

_START = time.monotonic()

SEQUENCE = {"OrderPlaced": 1, "OrderPaid": 2, "OrderPacked": 3, "OrderShipped": 4}
STATUS = {"OrderPlaced": "placed", "OrderPaid": "paid", "OrderPacked": "packed", "OrderShipped": "shipped"}


def now() -> float:
    """Seconds since the sandbox started (one clock for every record, like Day 10's dataset)."""
    return round(time.monotonic() - _START, 3)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class Event:
    """The event envelope from Day 10, Part 2.2."""

    type: str
    correlation_id: str
    order_id: str
    payload: dict[str, Any]
    sequence: int
    causation_id: str | None = None
    event_id: str = field(default_factory=lambda: new_id("e"))
    occurred_at: float = field(default_factory=now)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def first_event(event_type: str, correlation_id: str, order_id: str, payload: dict[str, Any]) -> Event:
    return Event(event_type, correlation_id, order_id, payload, SEQUENCE.get(event_type, 0))


def caused_by(cause: Event, event_type: str, payload: dict[str, Any] | None = None) -> Event:
    """The next event of the same flow: same correlation and order, causation = the cause."""
    return Event(
        event_type,
        cause.correlation_id,
        cause.order_id,
        payload or {},
        SEQUENCE[event_type],
        causation_id=cause.event_id,
    )


class MalformedOrderError(ValueError):
    """The order's items cannot be priced."""


def order_amount(payload: dict[str, Any]) -> str:
    """Total of ``items`` as a decimal string, or MalformedOrderError."""
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise MalformedOrderError("items must be a non-empty list")
    total = Decimal("0")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise MalformedOrderError(f"item {i} is not an object")
        quantity, price = item.get("quantity"), item.get("unit_price")
        if not isinstance(item.get("sku"), str) or not item["sku"]:
            raise MalformedOrderError(f"item {i}: sku missing")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise MalformedOrderError(f"item {i}: quantity must be a positive integer")
        try:
            unit = Decimal(str(price))
        except InvalidOperation:
            raise MalformedOrderError(f"item {i}: unit_price {price!r} is not a number") from None
        if not unit.is_finite() or unit < 0:
            raise MalformedOrderError(f"item {i}: unit_price {price!r} is not a price")
        total += unit * quantity
    return str(total)
