"""Base screen object: strict lookups, explicit waits, gestures. Selectors live only in screens."""

from __future__ import annotations

import re
from collections.abc import Callable

from appium.webdriver.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from framework.adapters.mobile.locators import Locator, by_accessibility_id, by_id
from framework.adapters.mobile.waits import visible, wait_until

ANDROID_BACK_KEY = 4


class Screen:
    """One app screen. ``wait_until_loaded`` proves the screen is shown, like web page objects."""

    def __init__(self, driver: WebDriver, timeout: float = 15.0) -> None:
        self.driver = driver
        self.timeout = timeout

    def wait_until_loaded(self) -> None:
        """Override: wait for the element that is unique to this screen."""

    # --- lookups -----------------------------------------------------------------
    def one(self, locator: Locator, within: WebElement | None = None) -> WebElement:
        """Exactly one match, or an error. Appium has no strict mode (Day 9, 3.4)."""
        root = within if within is not None else self.driver
        matches = root.find_elements(*locator.as_tuple())
        if len(matches) != 1:
            raise AssertionError(f"{locator.value!r} ({locator.layout}) matched {len(matches)} elements")
        return matches[0]

    def visible(self, locator: Locator) -> WebElement:
        return visible(self.driver, locator, self.timeout)

    def is_shown(self, locator: Locator) -> bool:
        return any(e.is_displayed() for e in self.driver.find_elements(*locator.as_tuple()))

    # --- actions -------------------------------------------------------------------
    def tap(self, locator: Locator) -> None:
        self.visible(locator).click()

    def type_into(self, locator: Locator, text: str) -> None:
        field = self.visible(locator)
        field.clear()
        field.send_keys(text)
        if self.driver.is_keyboard_shown():
            self.driver.hide_keyboard()

    def back(self) -> None:
        self.driver.execute_script("mobile: pressKey", {"keycode": ANDROID_BACK_KEY})

    def scroll_until(self, found: Callable[[], bool], container: Locator, max_swipes: int = 15) -> bool:
        """Scroll ``container`` down until ``found()``; stops when the list cannot scroll further.

        ``mobile: scrollGesture`` returns whether more scrolling is possible (driver source).
        ``percent`` is given as a fraction (Android's UiObject2 API); the driver's comments say
        "0-100" — confirm on the device (Day 9, Part 4).
        """
        for _ in range(max_swipes):
            if found():
                return True
            area = self.visible(container)
            can_scroll = self.driver.execute_script(
                "mobile: scrollGesture", {"elementId": area.id, "direction": "down", "percent": 0.75}
            )
            if not can_scroll:
                return found()
        return found()

    # --- header (present on most screens) ------------------------------------------
    def cart_count(self) -> int:
        badges = [e for e in self.driver.find_elements(*self._cart_count.as_tuple()) if e.is_displayed()]
        text = badges[0].text.strip() if badges else ""
        return int(text) if text.isdigit() else 0  # an empty cart may hide the badge

    def wait_for_cart_count(self, expected: int) -> None:
        """Evidence that an add/remove finished: the badge shows the new total."""
        wait_until(self.cart_count, lambda n: n == expected, timeout=self.timeout)

    def open_cart(self) -> None:
        self.tap(self._cart)

    # --- Locators (header: present on most screens) ----------------------------------
    _menu = by_accessibility_id("View menu", "menu_header_layout")
    _cart = by_accessibility_id("View cart", "menu_header_layout")
    _cart_count = by_id("cartTV", "menu_header_layout")


def number(text: str) -> int:
    """'3 items' -> 3."""
    match = re.search(r"\d+", text)
    if match is None:
        raise AssertionError(f"no number in {text!r}")
    return int(match.group())
