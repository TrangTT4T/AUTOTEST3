"""Browser monitor: network policy, request timings, console errors and dialogs of one context.

Network control has two jobs here:
* isolation and good citizenship - Swag Labs reports JavaScript errors to a third-party error
  tracker. Our deliberate fault personas would flood the vendor's tracker with noise, and a
  slow third party would make our timings flaky. Only allow-listed hosts are reached; every
  other request is aborted and counted (the evidence shows what was blocked);
* telemetry - start/end of every request, which swaglabs/perf.py turns into network-busy time.
  The times come from the BROWSER (``request.timing``), not from when Python received the event:
  Playwright's sync API delivers events late while the page's JavaScript is busy, and late
  timestamps once made a 5-second client-side delay look like 5 seconds of network traffic.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, ConsoleMessage, Dialog, Page, Request, Route

log = logging.getLogger("swaglabs.network")

ALLOWED_HOSTS = frozenset({"www.saucedemo.com", "fonts.googleapis.com", "fonts.gstatic.com"})


@dataclass
class BrowserMonitor:
    allowed_hosts: Collection[str] = ALLOWED_HOSTS
    clock: Callable[[], float] = time.time  # wall clock: comparable with the browser's timestamps
    blocked: Counter[str] = field(default_factory=Counter)
    console_errors: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    _started: dict[Request, float] = field(default_factory=dict)
    _intervals: list[tuple[float, float]] = field(default_factory=list)

    def attach(self, context: BrowserContext) -> None:
        # A predicate matcher: only foreign requests are routed; the shop's own go straight through.
        context.route(self._is_foreign, self._abort)
        context.on("page", self._watch)
        for page in context.pages:
            self._watch(page)

    def _is_foreign(self, url: str) -> bool:
        host = urlsplit(url).hostname or ""
        return urlsplit(url).scheme in {"http", "https"} and host not in self.allowed_hosts

    def _abort(self, route: Route) -> None:
        host = urlsplit(route.request.url).hostname or "?"
        self.blocked[host] += 1
        route.abort("blockedbyclient")

    def _watch(self, page: Page) -> None:
        page.on("request", self._on_request)
        page.on("requestfinished", self._on_request_done)
        page.on("requestfailed", self._on_request_done)
        page.on("console", self._on_console)
        page.on("pageerror", lambda error: self.console_errors.append(f"pageerror: {error}"))
        page.on("dialog", self._on_dialog)

    def _on_request(self, request: Request) -> None:
        self._started[request] = self.clock()

    def _on_request_done(self, request: Request) -> None:
        received = self._started.pop(request, None)
        timing = request.timing
        start_ms, end_offset_ms = timing.get("startTime", -1), timing.get("responseEnd", -1)
        if start_ms > 0 and end_offset_ms >= 0:  # the browser's own record of the request
            self._intervals.append((start_ms / 1000, (start_ms + end_offset_ms) / 1000))
        elif received is not None:  # failed or aborted requests have no timing: use what we saw
            self._intervals.append((received, self.clock()))

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error" and "ERR_BLOCKED_BY_CLIENT" not in message.text:
            self.console_errors.append(message.text)

    def _on_dialog(self, dialog: Dialog) -> None:
        # An unexpected alert() would otherwise block the page; record it, close it, let the
        # step that caused it decide whether it is a failure (see InventoryPage.sort_by).
        self.dialogs.append(dialog.message)
        log.warning("dialog %s: %s", dialog.type, dialog.message)
        dialog.dismiss()

    def finished(self) -> list[tuple[float, float]]:
        """(start, end) of every request that reported an end (finished or failed)."""
        return list(self._intervals)

    def in_flight_starts(self) -> list[float]:
        """Start times of requests that have not reported an end (yet)."""
        return list(self._started.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "blocked_hosts": dict(self.blocked),
            "console_errors": self.console_errors[-20:],
            "dialogs": self.dialogs,
            "requests_finished": len(self._intervals),
        }
