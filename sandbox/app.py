"""HTTP and WebSocket interface of the sandbox.

Public (what a client app would use):
    POST /orders                      -> 202 {order_id, correlation_id, replayed}
    GET  /orders/{order_id}           -> the read model, 404 until the projector has seen the order
    GET  /ws?correlation_id=&since=   -> live status frames; ``since`` = last frame number received

Observability (what a test environment exposes; every list needs ?correlation_id=):
    GET /config, /metrics, /events, /deliveries, /payments, /dlq

Control (test environments only):
    POST /admin/faults, /admin/publish, /admin/dlq/redrive, /admin/workers/{name}/stop|start
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import WSMsgType, web

from sandbox.broker import Broker
from sandbox.config import Config
from sandbox.faults import Fault, FaultError, Faults
from sandbox.model import MalformedOrderError, first_event, now
from sandbox.services import FulfilmentWorker, Gateway, Hub, Orders, PaymentsWorker, Projector

log = logging.getLogger("sandbox")
SYSTEM: web.AppKey[System] = web.AppKey("system")


class System:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.faults = Faults()
        self.broker = Broker(config.timings, self.faults)
        self.gateway = Gateway(config, self.faults)
        self.hub = Hub(config, self.faults)
        self.payments = PaymentsWorker(config, self.gateway, self.broker)
        self.fulfilment = FulfilmentWorker(config, self.broker)
        self.projector = Projector(config, self.hub)
        self.orders = Orders(self.broker)
        for worker in (self.payments, self.fulfilment, self.projector):
            workers = config.concurrency.get(worker.name, 1)
            self.broker.subscribe(worker.name, worker.types, worker.handle, workers)

    def start(self) -> None:
        self.broker.start()


Route = Callable[[web.Request], Awaitable[web.StreamResponse]]


@web.middleware
async def errors_as_json(request: web.Request, handler: Route) -> web.StreamResponse:
    try:
        return await handler(request)
    except (FaultError, MalformedOrderError, ValueError, TypeError, KeyError) as error:
        return web.json_response({"error": str(error)}, status=400)


def _system(request: web.Request) -> System:
    return request.app[SYSTEM]


def _correlation(request: web.Request) -> str:
    cid = request.query.get("correlation_id", "")
    if not cid:
        raise ValueError("correlation_id is required: filter by your own flow (Day 10, Part 2)")
    return cid


async def _body(request: web.Request) -> dict[str, Any]:
    data = await request.json()
    if not isinstance(data, dict):
        raise TypeError("the body must be a JSON object")
    return data


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} is required")
    return value


# --- public -------------------------------------------------------------------------
async def place_order(request: web.Request) -> web.Response:
    data = await _body(request)
    cid, key = _text(data, "correlation_id"), _text(data, "idempotency_key")
    items = data.get("items")
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    order_id, replayed = _system(request).orders.place(cid, key, items)
    return web.json_response({"order_id": order_id, "correlation_id": cid, "replayed": replayed}, status=202)


async def get_order(request: web.Request) -> web.Response:
    view = _system(request).projector.views.get(request.match_info["order_id"])
    if view is None or view["status"] is None:
        return web.json_response({"error": "unknown order (or not projected yet)"}, status=404)
    return web.json_response(view)


async def status_feed(request: web.Request) -> web.WebSocketResponse:
    cid = _correlation(request)
    since = int(request.query.get("since", "0"))
    hub = _system(request).hub
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await hub.attach(cid, since, ws)
    try:
        async for message in ws:  # clients send nothing; this waits until the socket closes
            if message.type == WSMsgType.ERROR:
                break
    finally:
        hub.detach(cid, ws)
    return ws


# --- observability ----------------------------------------------------------------
async def get_config(request: web.Request) -> web.Response:
    return web.json_response(_system(request).config.to_json())


async def get_metrics(request: web.Request) -> web.Response:
    """Point-in-time telemetry, like CloudWatch metrics: sampled during load tests (Unit 4, Day 16)."""
    system = _system(request)
    return web.json_response(
        {
            "at": now(),
            "subscriptions": system.broker.metrics(),
            "orders": len(system.projector.views),
            "charges": len(system.gateway.charges),
            "dead_letters": len(system.broker.dead_letters.entries),
        }
    )


async def get_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def list_events(request: web.Request) -> web.Response:
    cid = _correlation(request)
    events = [e.to_json() for e in _system(request).broker.published if e.correlation_id == cid]
    return web.json_response(events)


async def list_deliveries(request: web.Request) -> web.Response:
    return web.json_response(_system(request).broker.journal.for_correlation(_correlation(request)))


async def list_payments(request: web.Request) -> web.Response:
    cid = _correlation(request)
    return web.json_response([c for c in _system(request).gateway.charges if c["correlation_id"] == cid])


async def list_dead_letters(request: web.Request) -> web.Response:
    return web.json_response(_system(request).broker.dead_letters.for_correlation(_correlation(request)))


# --- control ---------------------------------------------------------------------------
async def add_fault(request: web.Request) -> web.Response:
    fault = _system(request).faults.add(Fault.from_json(await _body(request)))
    log.warning("fault added %s", fault)
    return web.json_response({"fault_id": fault.fault_id}, status=201)


async def publish_raw(request: web.Request) -> web.Response:
    """Another producer publishes an event directly (used for malformed messages)."""
    data = await _body(request)
    payload = data.get("payload", {})
    if not isinstance(payload, dict):
        raise TypeError("payload must be an object")
    event = first_event(_text(data, "type"), _text(data, "correlation_id"), _text(data, "order_id"), payload)
    _system(request).broker.publish(event)
    return web.json_response({"event_id": event.event_id}, status=202)


async def redrive(request: web.Request) -> web.Response:
    cid = _text(await _body(request), "correlation_id")
    return web.json_response({"redriven": _system(request).broker.redrive(cid)})


async def control_worker(request: web.Request) -> web.Response:
    name, action = request.match_info["name"], request.match_info["action"]
    subscription = _system(request).broker.subscriptions.get(name)
    if subscription is None or action not in {"stop", "start"}:
        raise ValueError(f"unknown worker {name!r} or action {action!r}")
    if action == "stop":
        subscription.running.clear()
    else:
        subscription.running.set()
    log.warning("worker %s %s", name, action)
    return web.json_response({"worker": name, "running": subscription.running.is_set()})


def create_app(system: System) -> web.Application:
    app = web.Application(middlewares=[errors_as_json])
    app[SYSTEM] = system
    app.add_routes(
        [
            web.post("/orders", place_order),
            web.get("/orders/{order_id}", get_order),
            web.get("/ws", status_feed),
            web.get("/config", get_config),
            web.get("/health", get_health),
            web.get("/metrics", get_metrics),
            web.get("/events", list_events),
            web.get("/deliveries", list_deliveries),
            web.get("/payments", list_payments),
            web.get("/dlq", list_dead_letters),
            web.post("/admin/faults", add_fault),
            web.post("/admin/publish", publish_raw),
            web.post("/admin/dlq/redrive", redrive),
            web.post("/admin/workers/{name}/{action}", control_worker),
        ]
    )
    return app
