"""pytest plugin: options, settings, catalogue, and the ``store`` fixture."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect
from playwright.sync_api import Error as PlaywrightError

from framework.adapters.fake import DEFAULT_SNAPSHOT, MOBILE_SNAPSHOT, FakeStore
from framework.adapters.mobile.store import MobileStore
from framework.adapters.web.diagnostics import BrowserDiagnostics
from framework.adapters.web.shop import Shop
from framework.adapters.web.store import WebStore
from framework.config import Settings, add_options
from framework.domain import Catalogue
from framework.errors import EnvironmentBlockedError
from framework.plugins.trace_steps import remember_page
from framework.ports import Store


def pytest_addoption(parser: pytest.Parser) -> None:
    add_options(parser)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Defaults for every browser context (extends pytest-playwright's own).

    The shop is British: pinning locale and time zone makes dates, number formats,
    and Accept-Language identical on every machine and in CI.
    Override per test with ``@pytest.mark.browser_context_args(...)``.
    """
    return {**browser_context_args, "locale": "en-GB", "timezone_id": "Europe/London"}


def configure_page(page: Page, settings: Settings) -> Page:
    """One place for browser-page defaults: every action and navigation waits up to --ui-timeout."""
    page.set_default_timeout(settings.ui_timeout_ms)
    return page


@pytest.fixture(scope="session", autouse=True)
def _expect_timeout(settings: Settings) -> None:
    """``expect(...)`` has its own default (5 s), separate from the page's: align it with --ui-timeout.

    Without this, page objects' "loaded" checks would ignore --ui-timeout and fail after 5 s on a
    slow environment while every click still waited the configured time.
    """
    expect.set_options(timeout=settings.ui_timeout_ms)


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    return Settings.from_pytest(pytestconfig)


@pytest.fixture(scope="session")
def live_catalogue(browser: Browser, settings: Settings) -> Catalogue:
    """Product data from the live /products.json, loaded ONCE per run (per xdist worker)."""
    context = browser.new_context(base_url=settings.base_url)
    try:
        response = context.new_page().goto("/products.json")
        try:
            data = response.json() if response else None
        except (ValueError, PlaywrightError):  # an HTML bot page instead of JSON, or no body
            data = None
        if data is None:
            raise EnvironmentBlockedError("/products.json did not return JSON")
        return Catalogue.from_products_json(data)
    finally:
        context.close()


@pytest.fixture
def store(request: pytest.FixtureRequest, settings: Settings) -> Iterator[Store]:
    """The Store adapter for this scenario. A new one (and a new cart) every time."""
    mobile_scenario = request.node.get_closest_marker("mobile") is not None
    if settings.store == "fake":
        yield FakeStore.from_snapshot(MOBILE_SNAPSHOT if mobile_scenario else DEFAULT_SNAPSHOT)
        return
    if settings.store == "mobile":
        driver = request.getfixturevalue("mobile_app")
        yield MobileStore(driver, request.getfixturevalue("mobile_catalogue"), settings.ui_timeout_ms / 1000)
        return

    page = configure_page(request.getfixturevalue("page"), settings)  # fresh browser context per test
    diagnostics = BrowserDiagnostics(settings.base_url)
    diagnostics.attach(page)
    remember_page(request.node, page)  # each Gherkin step becomes a group in the trace
    yield WebStore(page, request.getfixturevalue("live_catalogue"), diagnostics)
    # No clean-up request: the browser context (and its cart) is discarded by pytest-playwright.


@pytest.fixture(scope="session")
def catalogue_snapshot() -> Catalogue:
    """The recorded catalogue used by FakeStore (for unit tests and drift checks)."""
    return Catalogue.from_products_json(json.loads(DEFAULT_SNAPSHOT.read_text(encoding="utf-8")))


@pytest.fixture
def shop(page: Page, live_catalogue: Catalogue, settings: Settings) -> Shop:
    """Every page object, for plain Playwright tests (Unit 2): ``shop.catalog().open()``."""
    return Shop(configure_page(page, settings), live_catalogue)


@pytest.fixture
def new_shop(
    new_context: Callable[..., BrowserContext], live_catalogue: Catalogue, settings: Settings
) -> Callable[..., Shop]:
    """Factory: a new, isolated shopper (own browser context, own cart) per call.

    ``alice, bob = new_shop(), new_shop()``; context options pass through, e.g.
    ``new_shop(storage_state=path)``. pytest-playwright closes every context afterwards.
    """

    def make(**context_args: Any) -> Shop:
        return Shop(configure_page(new_context(**context_args).new_page(), settings), live_catalogue)

    return make
