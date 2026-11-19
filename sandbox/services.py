"""The services behind the broker: payment gateway, workers, read model, live status hub."""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import uuid
from collections import defaultdict
from typing import Any

from aiohttp import web

from sandbox.broker import Broker, PermanentError, TransientError
from sandbox.config import Config
from sandbox.faults import Faults
from sandbox.model import (
    STATUS,
    Event,
    MalformedOrderError,
    caused_by,
    first_event,
    new_id,
    now,
    order_amount,
)

log = logging.getLogger("sandbox")


class Gateway:
    """External payment provider. Idempotent per key, like real providers."""

    def __init__(self, config: Config, faults: Faults) -> None:
        self.config = config
        self.faults = faults
        self.charges: list[dict[str, Any]] = []
        self._by_key: dict[str, dict[str, Any]] = {}

    async def charge(self, key: str, event: Event, amount: str) -> dict[str, Any]:
        if self.faults.take("gateway_fail", event.correlation_id):
            raise TransientError("payment gateway: 503 Service Unavailable")
        slow = self.faults.take("gateway_slow", event.correlation_id)
        await asyncio.sleep(slow.seconds if slow else self.config.timings.gateway_latency)
        existing = self._by_key.get(key)
        if existing is not None:
            return existing
        charge = {
            "charge_id": new_id("ch"),
            "idempotency_key": key,
            "correlation_id": event.correlation_id,
            "order_id": event.order_id,
            "amount": amount,
            "at": now(),
        }
        self._by_key[key] = charge
        self.charges.append(charge)
        log.info("charge %s", json.dumps(charge))
        return charge


class PaymentsWorker:
    name = "payments"
    types = frozenset({"OrderPlaced"})

    def __init__(self, config: Config, gateway: Gateway, broker: Broker) -> None:
        self.config = config
        self.gateway = gateway
        self.broker = broker
        self.done: set[str] = set()
        self._calls: set[asyncio.Future[dict[str, Any]]] = set()

    async def handle(self, event: Event) -> str:
        if event.event_id in self.done:
            return "ignored: duplicate"
        try:
            amount = order_amount(event.payload)
        except MalformedOrderError as error:
            raise PermanentError(f"malformed OrderPlaced: {error}") from None
        key = f"pay-{event.order_id}"
        if self.config.has("per-attempt-payment-key"):
            key = f"{key}-{uuid.uuid4().hex[:6]}"
        call = asyncio.ensure_future(self.gateway.charge(key, event, amount))
        self._calls.add(call)  # the call goes on even if we stop waiting (a late answer)
        call.add_done_callback(self._finished)
        timeout = self.config.timings.gateway_timeout
        try:
            charge = await asyncio.wait_for(asyncio.shield(call), timeout)
        except TimeoutError:
            raise TransientError(f"payment gateway timeout after {timeout:g}s") from None
        self.broker.publish(
            caused_by(event, "OrderPaid", {"charge_id": charge["charge_id"], "amount": amount})
        )
        self.done.add(event.event_id)
        return "applied"

    def _finished(self, call: asyncio.Future[dict[str, Any]]) -> None:
        self._calls.discard(call)
        if not call.cancelled():
            call.exception()  # retrieved: a late failure is already handled by the retry


class FulfilmentWorker:
    name = "fulfilment"
    types = frozenset({"OrderPaid"})

    def __init__(self, config: Config, broker: Broker) -> None:
        self.config = config
        self.broker = broker
        self.done: set[str] = set()

    async def handle(self, event: Event) -> str:
        if event.event_id in self.done:
            return "ignored: duplicate"
        await asyncio.sleep(self.config.timings.step_delay)
        packed = caused_by(event, "OrderPacked")
        self.broker.publish(packed)
        await asyncio.sleep(self.config.timings.step_delay)
        self.broker.publish(caused_by(packed, "OrderShipped"))
        self.done.add(event.event_id)
        return "applied"


class Hub:
    """Live status frames per correlation id, with replay for clients that reconnect."""

    def __init__(self, config: Config, faults: Faults) -> None:
        self.config = config
        self.faults = faults
        self.frames: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.sockets: dict[str, set[web.WebSocketResponse]] = defaultdict(set)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def push(self, event: Event, status: str) -> None:
        cid = event.correlation_id
        async with self._locks[cid]:
            frames = self.frames[cid]
            frame = {
                "frame": len(frames) + 1,
                "order_id": event.order_id,
                "status": status,
                "sequence": event.sequence,
                "event_id": event.event_id,
                "at": now(),
            }
            frames.append(frame)
            log.info("frame %s %s", cid, json.dumps(frame))
            for ws in list(self.sockets[cid]):
                await _send(ws, frame)
            if self.faults.take("drop_connection", cid, status=status):
                log.warning("dropping %d connection(s) of %s (fault)", len(self.sockets[cid]), cid)
                for ws in list(self.sockets[cid]):
                    await ws.close(code=1012, message=b"sandbox: connection dropped (fault)")

    async def attach(self, cid: str, since: int, ws: web.WebSocketResponse) -> None:
        """Replay what the client missed, then send live frames. One lock: no gap, no overlap."""
        start = since + 1 if self.config.has("resume-skips-one-frame") and since > 0 else since
        async with self._locks[cid]:
            for frame in self.frames[cid]:
                if frame["frame"] > start:
                    await _send(ws, frame)
            self.sockets[cid].add(ws)

    def detach(self, cid: str, ws: web.WebSocketResponse) -> None:
        self.sockets[cid].discard(ws)


async def _send(ws: web.WebSocketResponse, frame: dict[str, Any]) -> None:
    if not ws.closed:
        try:
            await ws.send_json(frame)
        except ConnectionResetError:
            log.warning("client went away before frame %s", frame["frame"])


class Projector:
    """Builds the read model (what the order screen shows) and pushes status frames."""

    name = "projector"
    types = frozenset(STATUS)

    def __init__(self, config: Config, hub: Hub) -> None:
        self.config = config
        self.hub = hub
        self.views: dict[str, dict[str, Any]] = {}

    async def handle(self, event: Event) -> str:
        view = self.views.setdefault(
            event.order_id,
            {
                "order_id": event.order_id,
                "correlation_id": event.correlation_id,
                "status": None,
                "version": 0,
                "history": [],
                "updated_at": None,
            },
        )
        version = int(view["version"])
        if self.config.has("projector-ignores-sequence"):
            apply = event.sequence != version
        else:
            apply = event.sequence > version
        if not apply:
            if event.sequence == version:
                return "ignored: duplicate"
            return f"ignored: stale (sequence {event.sequence} < version {version})"
        status = STATUS[event.type]
        view.update(status=status, version=event.sequence, updated_at=now())
        view["history"].append(status)
        await self.hub.push(event, status)
        return "applied"


class Orders:
    """The synchronous front door: accepts an order, answers 202, and publishes OrderPlaced."""

    def __init__(self, broker: Broker) -> None:
        self.broker = broker
        self._by_key: dict[str, str] = {}
        self._numbers = itertools.count(1)

    def place(self, correlation_id: str, idempotency_key: str, items: list[Any]) -> tuple[str, bool]:
        """Return (order id, replayed). The same idempotency key never creates a second order."""
        if idempotency_key in self._by_key:
            return self._by_key[idempotency_key], True
        order_amount({"items": items})  # raises MalformedOrderError -> 400
        order_id = f"O-{next(self._numbers):05d}"
        self._by_key[idempotency_key] = order_id
        self.broker.publish(first_event("OrderPlaced", correlation_id, order_id, {"items": items}))
        return order_id, False
