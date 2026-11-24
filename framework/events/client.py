"""HTTP clients for the order-events system: one transport, one client per domain.

    BaseClient            transport only: base URL, headers (and an optional bearer token), timeout,
                          expected statuses, error classification. No business knowledge.
    OrdersClient          the customer-facing API: place an order, read it, the live-status URL
    ObservabilityClient   what the system recorded: events, deliveries, payments, dead letters
    AdminClient           test-environment control: faults, raw publishing, redrive, workers
    SandboxApi            the three domain clients over one base URL (what fixtures hand out)

Rules (checked by tests/unit/test_architecture.py):
* a client returns typed models (``framework/events/model.py``), parsed and validated from JSON;
* a client never asserts: an unexpected status is an ``ApiRequestError`` (our request or the
  environment is wrong), never an ``AssertionError`` (which this project reserves for product
  defects found by a test, and which strict xfails accept);
* tests never build clients: fixtures do (framework/plugins/events.py).

Keeping the admin endpoints in their own client means a suite pointed at a real environment can be
given ``OrdersClient`` alone: the control endpoints are not reachable from its code at all.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from framework.errors import ApiRequestError, EnvironmentBlockedError
from framework.events.model import Charge, DeadLetter, Delivery, Fault, Item, OrderView, SandboxInfo


class SandboxRequestError(ApiRequestError):
    """The order-events system refused a request the test framework made (a framework or test bug)."""


class BaseClient:
    """Transport shared by every domain client. Subclasses add endpoints, never transport logic."""

    def __init__(self, base_url: str, *, timeout: float = 5.0, token: str | None = None) -> None:
        if urllib.parse.urlparse(base_url).scheme not in {"http", "https"}:
            raise ValueError(f"the order-events system must be an http(s) URL, got {base_url!r}")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        # A local system must never be reached through a corporate or CI proxy.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def __repr__(self) -> str:  # never print the token
        return f"{type(self).__name__}({self.base_url!r})"

    def _call(self, method: str, path: str, body: Any = None, **query: str) -> tuple[int, Any]:
        """(status, parsed JSON or raw text). Only an unreachable system raises here."""
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(  # noqa: S310 - http(s) only: checked in __init__
            url,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            method=method,
            headers=self._headers,
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace")
            try:
                return error.code, json.loads(text)
            except ValueError:
                return error.code, text
        except (urllib.error.URLError, OSError) as error:
            raise EnvironmentBlockedError(
                f"order-events system unreachable at {self.base_url}: {error}"
            ) from error

    def _expect(self, statuses: Iterable[int], method: str, path: str, body: Any = None, **query: str) -> Any:
        """The parsed body when the status is one of ``statuses``; otherwise ``SandboxRequestError``."""
        status, data = self._call(method, path, body, **query)
        if status not in set(statuses):
            raise SandboxRequestError(f"{method} {path} {query or ''} -> HTTP {status}: {data}")
        return data


class OrdersClient(BaseClient):
    """The API a customer's app uses."""

    def info(self) -> SandboxInfo:
        return SandboxInfo.from_json(self._expect({200}, "GET", "/config"))

    def place_order(
        self, correlation_id: str, items: Iterable[Item], idempotency_key: str
    ) -> tuple[str, bool]:
        """Returns (order id, replayed). 202 Accepted means accepted, not done (Day 10, Part 0)."""
        body = {
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "items": [item.to_json() for item in items],
        }
        data = self._expect({202}, "POST", "/orders", body)
        return str(data["order_id"]), bool(data["replayed"])

    def order(self, order_id: str) -> OrderView | None:
        status, data = self._call("GET", f"/orders/{order_id}")
        if status == 404:
            return None  # not projected yet: eventual consistency, not an error
        if status != 200:
            raise SandboxRequestError(f"GET /orders/{order_id} -> HTTP {status}: {data}")
        return OrderView.from_json(data)

    def ws_url(self, correlation_id: str, since: int = 0) -> str:
        query = urllib.parse.urlencode({"correlation_id": correlation_id, "since": since})
        return f"{self.base_url.replace('http', 'ws', 1)}/ws?{query}"


class ObservabilityClient(BaseClient):
    """What the system recorded, filtered by correlation id (read-only)."""

    def events(self, correlation_id: str) -> list[dict[str, Any]]:
        return list(self._expect({200}, "GET", "/events", correlation_id=correlation_id))

    def deliveries(self, correlation_id: str) -> list[Delivery]:
        rows = self._expect({200}, "GET", "/deliveries", correlation_id=correlation_id)
        return [Delivery.from_json(r) for r in rows]

    def charges(self, correlation_id: str) -> list[Charge]:
        rows = self._expect({200}, "GET", "/payments", correlation_id=correlation_id)
        return [Charge.from_json(r) for r in rows]

    def dead_letters(self, correlation_id: str) -> list[DeadLetter]:
        rows = self._expect({200}, "GET", "/dlq", correlation_id=correlation_id)
        return [DeadLetter.from_json(r) for r in rows]

    def raw(self, path: str, correlation_id: str) -> Any:
        """The unparsed JSON, for evidence files."""
        return self._expect({200}, "GET", path, correlation_id=correlation_id)


class AdminClient(BaseClient):
    """Control endpoints that exist only in test environments."""

    def inject(self, correlation_id: str, fault: Fault) -> str:
        data = self._expect({201}, "POST", "/admin/faults", fault.to_json(correlation_id))
        return str(data["fault_id"])

    def publish_raw(
        self, correlation_id: str, event_type: str, order_id: str, payload: dict[str, Any]
    ) -> str:
        body = {
            "correlation_id": correlation_id,
            "type": event_type,
            "order_id": order_id,
            "payload": payload,
        }
        return str(self._expect({202}, "POST", "/admin/publish", body)["event_id"])

    def redrive(self, correlation_id: str) -> int:
        data = self._expect({200}, "POST", "/admin/dlq/redrive", {"correlation_id": correlation_id})
        return int(data["redriven"])

    def stop_worker(self, name: str) -> None:
        self._expect({200}, "POST", f"/admin/workers/{name}/stop", {})

    def start_worker(self, name: str) -> None:
        self._expect({200}, "POST", f"/admin/workers/{name}/start", {})


@dataclass(frozen=True)
class SandboxApi:
    """The domain clients of one environment, built once and injected by fixtures."""

    orders: OrdersClient
    observe: ObservabilityClient
    admin: AdminClient

    @classmethod
    def connect(cls, base_url: str, *, timeout: float = 5.0, token: str | None = None) -> SandboxApi:
        options: dict[str, Any] = {"timeout": timeout, "token": token}
        return cls(
            OrdersClient(base_url, **options),
            ObservabilityClient(base_url, **options),
            AdminClient(base_url, **options),
        )
