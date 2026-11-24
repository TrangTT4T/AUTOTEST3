"""``SwagLabs``: the one object step definitions talk to.

It owns the browser page, the run settings, the reference catalogue, the browser monitor and
the performance recorder, and hands out page objects. Steps never touch Playwright directly
(tests/unit/test_architecture.py checks this), so a UI change is fixed in one page object.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from playwright.sync_api import Page

from swaglabs.config import Settings
from swaglabs.domain import Catalogue, Product
from swaglabs.network import BrowserMonitor
from swaglabs.pages import (
    CartPage,
    CheckoutCompletePage,
    CheckoutInfoPage,
    CheckoutOverviewPage,
    Header,
    InventoryPage,
    LazyLoadCatalogPage,
    LoginPage,
    ProductPage,
    SliderCatalogPage,
    SpinnerCatalogPage,
)
from swaglabs.perf import Measurement, busy_time, window_activity
from swaglabs.waiting import eventually

SESSION_COOKIE = "session-username"
CART_STORAGE_KEY = "cart-contents"


@dataclass
class PerfRecorder:
    """Times interactions and splits each into network-busy and client time."""

    monitor: BrowserMonitor
    test: str = ""
    measurements: list[Measurement] = field(default_factory=list)

    @contextmanager
    def measure(self, action: str) -> Iterator[None]:
        """Time the block. Put the action AND the wait for its visible outcome inside it."""
        # Duration from the monotonic clock (immune to clock adjustments); the window for matching
        # requests from the wall clock, which is what the browser's request timestamps use.
        start, wall_start = time.monotonic(), time.time()
        yield
        end, wall_end = time.monotonic(), time.time()
        intervals, requests = window_activity(
            self.monitor.finished(), self.monitor.in_flight_starts(), wall_start, wall_end
        )
        self.measurements.append(
            Measurement(
                action=action,
                duration_ms=round((end - start) * 1000, 1),
                network_busy_ms=round(busy_time(intervals, wall_start, wall_end) * 1000, 1),
                requests=requests,
                test=self.test,
            )
        )

    def last(self, action: str) -> Measurement:
        for m in reversed(self.measurements):
            if m.action == action:
                return m
        raise LookupError(f"no '{action}' measurement in this test; did the step use perf.measure?")


class SwagLabs:
    def __init__(
        self,
        page: Page,
        settings: Settings,
        catalogue: Catalogue,
        monitor: BrowserMonitor,
        perf: PerfRecorder,
    ) -> None:
        self.page = page
        self.settings = settings
        self.catalogue = catalogue
        self.monitor = monitor
        self.perf = perf

    # --- page objects (cheap: a new one per call, always bound to the current page) ---
    def login_page(self) -> LoginPage:
        return LoginPage(self.page)

    def inventory(self) -> InventoryPage:
        return InventoryPage(self.page)

    def product(self) -> ProductPage:
        return ProductPage(self.page)

    def cart(self) -> CartPage:
        return CartPage(self.page)

    def checkout_info(self) -> CheckoutInfoPage:
        return CheckoutInfoPage(self.page)

    def overview(self) -> CheckoutOverviewPage:
        return CheckoutOverviewPage(self.page)

    def complete(self) -> CheckoutCompletePage:
        return CheckoutCompletePage(self.page)

    def spinner_catalogue(self) -> SpinnerCatalogPage:
        return SpinnerCatalogPage(self.page)

    def lazy_catalogue(self) -> LazyLoadCatalogPage:
        return LazyLoadCatalogPage(self.page)

    def slider(self) -> SliderCatalogPage:
        return SliderCatalogPage(self.page)

    @property
    def header(self) -> Header:
        return Header(self.page)

    # --- browser navigation (steps never call Playwright themselves) ----------
    def visit(self, path: str) -> None:
        self.page.goto(path)

    def reload(self) -> None:
        self.page.reload()

    def go_back(self) -> None:
        self.page.go_back()

    def new_tab(self) -> SwagLabs:
        """A second tab in the SAME browser context: same cookies, same localStorage."""
        return SwagLabs(self.page.context.new_page(), self.settings, self.catalogue, self.monitor, self.perf)

    def fits_screen_width(self) -> bool:
        """No sideways scrolling: the document is not wider than the viewport."""
        return bool(self.page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))

    # --- sessions ------------------------------------------------------------
    def log_in_with_form(self, username: str, password: str) -> None:
        """The real login: what REQ-SL-01/02 test. Timed as ``login`` when it succeeds."""
        login = self.login_page()
        login.wait_until_loaded()
        with self.perf.measure("login"):
            login.log_in(username, password)
            self.inventory().wait_until_loaded()

    def start_session(self) -> InventoryPage:
        """Fast path for scenarios that are not ABOUT logging in: set the session cookie directly.

        The shop keeps its whole session in one cookie; the contract scenario
        "The quick-login shortcut creates the same session as the login form" proves that the
        form sets exactly this cookie, so the shortcut stays honest if the shop changes.
        """
        self.page.context.add_cookies(
            [{"name": SESSION_COOKIE, "value": self.settings.persona.value, "url": self.settings.base_url}]
        )
        return self.inventory().open()

    def session_user(self) -> str | None:
        cookies = self.page.context.cookies(self.settings.base_url)
        return next((c["value"] for c in cookies if c["name"] == SESSION_COOKIE), None)

    # --- cart state (the shop keeps it in localStorage) -----------------------
    def seed_cart(self, products: Iterable[Product]) -> None:
        """Arrange a cart through the state store, then reload: fast, and independent of the
        add-to-cart buttons (which some personas break). Act through the UI, arrange through state."""
        ids = [p.id for p in products]
        self.page.evaluate(
            "([key, ids]) => localStorage.setItem(key, JSON.stringify(ids))", [CART_STORAGE_KEY, ids]
        )
        self.page.reload()

    def stored_cart_ids(self) -> list[int]:
        raw = self.page.evaluate("(key) => localStorage.getItem(key)", CART_STORAGE_KEY)
        return [int(i) for i in json.loads(raw)] if raw else []

    def eventually_stored_cart(self, expected: list[int]) -> list[int]:
        """Wait until the stored cart holds ``expected`` (order-insensitive)."""
        return self.eventually(
            self.stored_cart_ids,
            lambda ids: sorted(ids) == sorted(expected),
            f"stored cart should hold product ids {sorted(expected)}",
        )

    def eventually[T](self, probe: Callable[[], T], predicate: Callable[[T], bool], description: str) -> T:
        """``waiting.eventually`` with the UI timeout, sleeping INSIDE Playwright so that browser
        events (requests, dialogs) keep being delivered while we wait."""
        return eventually(
            probe,
            predicate,
            timeout_s=self.settings.ui_timeout_ms / 1000,
            description=description,
            sleep=lambda seconds: self.page.wait_for_timeout(seconds * 1000),
        )
