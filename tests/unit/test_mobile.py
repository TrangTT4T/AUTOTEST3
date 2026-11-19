"""Mobile adapter logic that can be checked without a device."""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from framework.adapters.fake import MOBILE_SNAPSHOT, FakeStore
from framework.adapters.mobile.capabilities import APP_ACTIVITY, APP_PACKAGE, android_capabilities
from framework.adapters.mobile.evidence import safe_capabilities
from framework.adapters.mobile.locators import Locator
from framework.adapters.mobile.screens import ALL_SCREENS
from framework.adapters.mobile.session import is_environment_problem
from framework.adapters.mobile.store import MobileStore
from framework.config import Settings
from framework.domain import Cart, CartLine, Catalogue, Money
from framework.errors import CartInconsistencyError

INVENTORY = json.loads((Path(__file__).parents[1] / "data" / "mobile_ui_inventory.json").read_text("utf-8"))


def _settings(**overrides: str) -> Settings:
    values = {
        "base_url": "https://shop",
        "store": "mobile",
        "ui_timeout_ms": 15000,
        "fail_on_uncovered": False,
    }
    return Settings(**{**values, **overrides})  # type: ignore[arg-type]


# --- capabilities ------------------------------------------------------------------
def test_capabilities_pin_what_affects_results() -> None:
    caps = android_capabilities(_settings())
    assert caps["platformName"] == "Android"
    assert caps["automationName"] == "UIAutomator2"
    assert (caps["appium:appPackage"], caps["appium:appActivity"]) == (APP_PACKAGE, APP_ACTIVITY)
    assert (caps["appium:language"], caps["appium:locale"]) == ("en", "US")
    assert caps["appium:autoGrantPermissions"] is True
    assert caps["appium:disableWindowAnimation"] is True
    assert "appium:app" not in caps  # only when given
    assert "appium:avd" not in caps


def test_machine_specific_values_come_from_settings() -> None:
    caps = android_capabilities(_settings(android_app="/apps/mda.apk", android_avd="Pixel_8"))
    assert caps["appium:app"] == "/apps/mda.apk"
    assert caps["appium:avd"] == "Pixel_8"


# --- locator contract against the app's own layouts -----------------------------------
LOCATORS = [
    (screen.__name__, name, value)
    for screen in ALL_SCREENS
    for name, value in vars(screen).items()
    if isinstance(value, Locator)
]


@pytest.mark.parametrize(("screen", "name", "locator"), LOCATORS, ids=[f"{s}.{n}" for s, n, _ in LOCATORS])
def test_every_locator_exists_in_the_app(screen: str, name: str, locator: Locator) -> None:
    layout = INVENTORY["layouts"].get(locator.layout)
    assert layout is not None, f"{screen}.{name}: no layout {locator.layout!r} in the app"
    if locator.by == AppiumBy.ID:
        assert locator.value in layout, f"{screen}.{name}: id {locator.value!r} not in {locator.layout}"
    elif locator.by == AppiumBy.XPATH:  # structural: every id it mentions must exist in the layout
        ids = re.findall(r"@resource-id, '(\w+)'", locator.value)
        assert ids, f"{screen}.{name}: XPath names no resource id to anchor on"
        assert all(i in layout for i in ids), f"{screen}.{name}: {ids} not all in {locator.layout}"
    else:
        matches = [i for i, e in layout.items() if e["content_description"] == locator.value]
        assert len(matches) == 1, f"{screen}.{name}: {locator.value!r} matches {matches} in {locator.layout}"


# --- environment classification ---------------------------------------------------------
@pytest.mark.parametrize(
    "message",
    [
        "Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported.",  # seen on Day 9
        "Could not find a connected Android device in 20000ms.",
        "HTTPConnectionPool(host='127.0.0.1', port=4723): Max retries exceeded with url: /session",
    ],
)
def test_environment_problems_are_recognised(message: str) -> None:
    assert is_environment_problem(message)


@pytest.mark.parametrize(
    "message",
    [
        "An element could not be located on the page using the given search parameters.",
        "AssertionError: total",
    ],
)
def test_app_problems_are_not_hidden_as_environment(message: str) -> None:
    assert not is_environment_problem(message)


# --- data and domain ---------------------------------------------------------------------
def test_mobile_catalogue_facts() -> None:
    catalogue = Catalogue.from_products_json(json.loads(MOBILE_SNAPSHOT.read_text("utf-8")))
    assert catalogue.currency == "USD"
    assert len(catalogue.names()) == 24
    assert catalogue.by_name("Sauce Labs Backpack").price == Money(Decimal("29.99"), "USD")
    assert catalogue.by_name("Sauce Labs Bike Light").price == Money(Decimal("9.99"), "USD")
    assert catalogue.sold_out() == []


def test_the_apps_price_format_is_read() -> None:
    assert Money.parse("$ 45.97", "USD") == Money(
        Decimal("45.97"), "USD"
    )  # CartFragment: CURRENCY + " " + total
    assert str(Money(Decimal("45.97"), "USD")) == "$45.97"


def test_fake_store_uses_the_catalogue_currency() -> None:
    store = FakeStore.from_snapshot(MOBILE_SNAPSHOT)
    store.prefill({"Sauce Labs Backpack": 2})
    assert store.cart().total == Money(Decimal("59.98"), "USD")


# --- cart consistency on one screen -------------------------------------------------------
def _cart(qty: int, line_total: str, total: str) -> Cart:
    line = CartLine("Sauce Labs Backpack", "", qty, Money(Decimal(line_total), "USD"))
    return Cart((line,), Money(Decimal(total), "USD"))


def test_consistent_cart_screen_passes() -> None:
    MobileStore._check_consistent(_cart(2, "59.98", "59.98"), badge=2, items_label=2)


@pytest.mark.parametrize(
    ("cart", "badge", "label", "message"),
    [
        (_cart(2, "59.98", "29.99"), 2, 2, "total"),
        (_cart(2, "59.98", "59.98"), 1, 2, "header badge"),
        (_cart(2, "59.98", "59.98"), 2, 3, "items' label"),
    ],
)
def test_inconsistent_cart_screen_is_a_defect(cart: Cart, badge: int, label: int, message: str) -> None:
    with pytest.raises(CartInconsistencyError, match=message):
        MobileStore._check_consistent(cart, badge=badge, items_label=label)


def test_secrets_are_masked_in_reported_capabilities() -> None:
    caps = safe_capabilities({"appium:deviceName": "Pixel", "sauce:accessKey": "abc", "appium:password": "x"})
    assert caps == {"appium:deviceName": "Pixel", "sauce:accessKey": "***", "appium:password": "***"}
