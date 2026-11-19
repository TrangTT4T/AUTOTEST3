"""In-memory broker with at-least-once delivery (Day 10, Part 1).

Each subscription has its own queue and processes one message at a time.
After the handler returns, the message is acknowledged; if the acknowledgement is lost,
the message is delivered again after the visibility timeout. A transient error is retried
with exponential backoff; after ``max_attempts`` the message goes to the dead-letter queue.
A permanent error goes there at once: retrying a malformed message cannot help.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sandbox.config import Timings
from sandbox.faults import Faults
from sandbox.model import Event, now

log = logging.getLogger("sandbox")

Handler = Callable[[Event], Awaitable[str]]


class TransientError(Exception):
    """Worth retrying: a timeout, a 503."""


class PermanentError(Exception):
    """Retrying cannot help: the message itself is wrong."""


@dataclass(frozen=True)
class Delivery:
    event: Event
    number: int  # 1 = first delivery of this event to this subscription
    reason: str  # first | retry | redelivery (no ack) | duplicate | released after <type> | redrive


class Journal:
    """Every delivery and its result: the event-correlation data that GET /deliveries returns."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def add(self, subscription: str, delivery: Delivery, result: str, detail: str = "") -> None:
        event = delivery.event
        record = {
            "at": now(),
            "correlation_id": event.correlation_id,
            "order_id": event.order_id,
            "subscription": subscription,
            "event_id": event.event_id,
            "type": event.type,
            "sequence": event.sequence,
            "delivery": delivery.number,
            "reason": delivery.reason,
            "result": result,
            "detail": detail,
        }
        self.records.append(record)
        log.info("delivery %s", json.dumps(record))

    def for_correlation(self, correlation_id: str) -> list[dict[str, Any]]:
        return [r for r in self.records if r["correlation_id"] == correlation_id]


class DeadLetters:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def add(self, subscription: str, delivery: Delivery, error: str) -> None:
        entry = {
            "at": now(),
            "correlation_id": delivery.event.correlation_id,
            "subscription": subscription,
            "event": delivery.event.to_json(),
            "attempts": delivery.number,
            "error": error,
        }
        self.entries.append(entry)
        log.warning("dead-letter %s", json.dumps(entry))

    def for_correlation(self, correlation_id: str) -> list[dict[str, Any]]:
        return [e for e in self.entries if e["correlation_id"] == correlation_id]

    def take(self, correlation_id: str) -> list[dict[str, Any]]:
        taken = self.for_correlation(correlation_id)
        self.entries = [e for e in self.entries if e["correlation_id"] != correlation_id]
        return taken


class Subscription:
    def __init__(
        self, name: str, types: frozenset[str], handler: Handler, broker: Broker, concurrency: int = 1
    ) -> None:
        self.name = name
        self.concurrency = concurrency
        self.in_flight = 0
        self.processed = 0  # deliveries the handler completed (applied or ignored)
        self.failed = 0
        self.types = types
        self.handler = handler
        self.broker = broker
        self.queue: asyncio.Queue[Delivery] = asyncio.Queue()
        self.running = asyncio.Event()
        self.running.set()
        self.held: list[tuple[str, str, Delivery]] = []  # (correlation id, after_type, delivery)
        self.counts: dict[str, int] = {}  # event_id -> deliveries so far
        self.tasks: list[asyncio.Task[None]] = []

    def offer(self, event: Event, reason: str = "first") -> None:
        number = self.counts.get(event.event_id, 0) + 1
        self.counts[event.event_id] = number
        self.queue.put_nowait(Delivery(event, number, reason))

    def offer_later(self, event: Event, reason: str, delay: float) -> None:
        asyncio.get_running_loop().call_later(delay, self.offer, event, reason)

    async def run(self) -> None:
        while True:
            delivery = await self.queue.get()
            await self.running.wait()  # a stopped worker keeps its messages queued
            await self.process(delivery)

    async def process(self, d: Delivery) -> None:
        event, faults, timings = d.event, self.broker.faults, self.broker.timings
        scope = (event.correlation_id, self.name, event.type)

        delay = faults.take("delay", *scope)
        if delay:
            await asyncio.sleep(delay.seconds)
        if not d.reason.startswith("released"):
            hold = faults.take("deliver_after", *scope)
            if hold and hold.after_type:
                self.held.append((event.correlation_id, hold.after_type, d))
                self.broker.journal.add(self.name, d, "held", f"until {hold.after_type} is delivered")
                return
        if faults.take("duplicate", *scope):
            self.offer(event, "duplicate")

        self.in_flight += 1
        try:
            result = await self.handler(event)
        except PermanentError as error:
            self.failed += 1
            self.broker.journal.add(self.name, d, "dead-lettered", f"permanent: {error}")
            self.broker.dead_letters.add(self.name, d, f"permanent: {error}")
            return
        except Exception as error:  # noqa: BLE001 - a broker treats any other consumer error as transient
            self.failed += 1
            if d.number >= timings.max_attempts:
                self.broker.journal.add(self.name, d, "dead-lettered", f"{error}; attempts exhausted")
                self.broker.dead_letters.add(self.name, d, str(error))
            else:
                wait = timings.backoff(d.number)
                self.broker.journal.add(self.name, d, "failed", f"{error}; retry in {wait:g}s")
                self.offer_later(event, "retry", wait)
            return
        finally:
            self.in_flight -= 1

        self.processed += 1
        if faults.take("lose_ack", *scope):
            self.broker.journal.add(self.name, d, result, "acknowledgement lost")
            self.offer_later(event, "redelivery (no ack)", timings.visibility_timeout)
        else:
            self.broker.journal.add(self.name, d, result)
        self._release_held(event)

    def _release_held(self, delivered: Event) -> None:
        still_held = []
        for correlation_id, after_type, held in self.held:
            if correlation_id == delivered.correlation_id and after_type == delivered.type:
                self.queue.put_nowait(Delivery(held.event, held.number, f"released after {after_type}"))
            else:
                still_held.append((correlation_id, after_type, held))
        self.held = still_held


class Broker:
    def __init__(self, timings: Timings, faults: Faults) -> None:
        self.timings = timings
        self.faults = faults
        self.subscriptions: dict[str, Subscription] = {}
        self.journal = Journal()
        self.dead_letters = DeadLetters()
        self.published: list[Event] = []

    def subscribe(self, name: str, types: frozenset[str], handler: Handler, concurrency: int = 1) -> None:
        self.subscriptions[name] = Subscription(name, types, handler, self, concurrency)

    def publish(self, event: Event) -> None:
        self.published.append(event)
        log.info("publish %s", json.dumps(event.to_json()))
        for subscription in self.subscriptions.values():
            if event.type in subscription.types:
                subscription.offer(event)

    def start(self) -> None:
        for s in self.subscriptions.values():
            s.tasks = [asyncio.create_task(s.run(), name=f"{s.name}-{i}") for i in range(s.concurrency)]

    def metrics(self) -> dict[str, dict[str, int]]:
        """Per subscription: the numbers a CloudWatch dashboard would show for a queue and its consumers."""
        return {
            name: {
                "queued": s.queue.qsize(),
                "in_flight": s.in_flight,
                "processed": s.processed,
                "failed": s.failed,
                "held": len(s.held),
                "workers": s.concurrency,
            }
            for name, s in self.subscriptions.items()
        }

    def redrive(self, correlation_id: str) -> int:
        """Move this flow's dead letters back to their subscriptions, attempts counted afresh."""
        entries = self.dead_letters.take(correlation_id)
        for entry in entries:
            subscription = self.subscriptions[entry["subscription"]]
            event = Event(**entry["event"])
            subscription.counts[event.event_id] = 0
            subscription.offer(event, "redrive")
        return len(entries)
