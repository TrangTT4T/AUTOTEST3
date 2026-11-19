"""``OrderFlow``: one business flow under test — its correlation id, faults, live stream, and order.

Tests read like the business story; every observation is filtered by the flow's own
correlation id, so tests can run in parallel against one system (Day 10, Part 2.4).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any

from framework.events.client import OrdersClient
from framework.events.model import Charge, DeadLetter, Delivery, Fault, Frame, Item, OrderView, SandboxInfo
from framework.events.stream import StatusStream
from framework.waiting import wait_until, wait_until_stable

DEFAULT_ITEMS = (Item("SL-BACKPACK", 2, Decimal("29.99")),)


class OrderFlow:
    def __init__(self, client: OrdersClient, info: SandboxInfo, correlation_id: str) -> None:
        self.client = client
        self.info = info
        self.correlation_id = correlation_id
        self.stream = StatusStream(lambda since: client.ws_url(correlation_id, since))
        self.faults: list[Fault] = []
        self.order_id: str | None = None
        self.placed_at: float | None = None
        self.converged_in: float | None = None  # seconds from the action to the awaited status

    # --- acting ---------------------------------------------------------------------------
    def follow(self) -> None:
        """Subscribe to the live status before anything happens (push, not pull)."""
        self.stream.connect()

    def inject(self, fault: Fault) -> None:
        self.client.inject(self.correlation_id, fault)
        self.faults.append(fault)

    def place(self, items: Sequence[Item] = DEFAULT_ITEMS, idempotency_key: str | None = None) -> str:
        key = idempotency_key or f"{self.correlation_id}-order"
        self.placed_at = time.monotonic()
        self.order_id, _ = self.client.place_order(self.correlation_id, items, key)
        return self.order_id

    def publish_malformed_order(self) -> str:
        """Another producer sends an OrderPlaced the payments worker cannot price."""
        self.order_id = f"BAD-{self.correlation_id[-8:]}"
        return self.client.publish_raw(self.correlation_id, "OrderPlaced", self.order_id, {"items": []})

    # --- waiting for outcomes ---------------------------------------------------------------
    def wait_for_status(
        self, status: str, timeout: float | None = None, measured_from: float | None = None
    ) -> Frame:
        """Wait for the pushed status; record how long it took (the consistency target by default)."""
        frame = self.stream.wait_for_status(status, timeout or self.info.consistency_target)
        start = measured_from if measured_from is not None else self.placed_at
        if start is not None:
            self.converged_in = round(frame.received_at - start, 3)
        return frame

    def wait_for_view_status(self, status: str, timeout: float | None = None) -> OrderView:
        """Poll the read model (pull) until it shows ``status``."""
        view = wait_until(
            self.view,
            lambda v: v is not None and v.status == status,
            timeout=timeout or self.info.consistency_target,
        )
        if view is None:  # wait_until only returns once the view exists; this narrows the type
            raise RuntimeError(f"order {self.order_id} has no read model")
        return view

    def wait_for_deliveries(
        self,
        subscription: str,
        event_type: str,
        count: int,
        where: Callable[[Delivery], bool] | None = None,
        timeout: float | None = None,
    ) -> list[Delivery]:
        """Wait until ``count`` matching deliveries are journalled: evidence that processing finished."""
        return wait_until(
            lambda: [d for d in self.deliveries(subscription, event_type) if where is None or where(d)],
            lambda found: len(found) >= count,
            timeout=timeout or self.info.consistency_target + self.info.retry_budget,
        )

    def wait_for_dead_letters(self, count: int = 1, timeout: float | None = None) -> list[DeadLetter]:
        return wait_until(
            self.dead_letters,
            lambda letters: len(letters) >= count,
            timeout=timeout or self.info.retry_budget + self.info.consistency_target,
        )

    def settle(self) -> None:
        """Wait until this flow has gone quiet: no new delivery, charge, or frame for the quiet period."""
        wait_until_stable(
            lambda: (len(self.deliveries()), len(self.charges()), len(self.stream.frames)),
            quiet=self.info.quiet_period,
            timeout=self.info.consistency_target + self.info.retry_budget + self.info.quiet_period,
        )

    # --- observing ----------------------------------------------------------------------------
    def view(self) -> OrderView | None:
        if not self.order_id:
            raise RuntimeError("no order placed in this flow: call place() first")
        return self.client.order(self.order_id)

    def statuses(self) -> list[str]:
        return self.stream.statuses()

    def charges(self) -> list[Charge]:
        return self.client.charges(self.correlation_id)

    def deliveries(self, subscription: str | None = None, event_type: str | None = None) -> list[Delivery]:
        return [
            d
            for d in self.client.deliveries(self.correlation_id)
            if subscription in (None, d.subscription) and event_type in (None, d.type)
        ]

    def published(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.client.events(self.correlation_id) if e["type"] == event_type]

    def dead_letters(self) -> list[DeadLetter]:
        return self.client.dead_letters(self.correlation_id)

    def close(self) -> None:
        self.stream.close()
