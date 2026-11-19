"""Explicit waits for Appium. Appium has no automatic waiting (Day 9, Part 5).

Rule: implicit wait 0; every wait is explicit, for a condition, with a deadline.
"""

from __future__ import annotations

from appium.webdriver.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from framework.adapters.mobile.locators import Locator
from framework.waiting import wait_until

__all__ = ["visible", "wait_until"]


def visible(driver: WebDriver, locator: Locator, timeout: float) -> WebElement:
    element: WebElement = WebDriverWait(driver, timeout).until(
        ec.visibility_of_element_located(locator.as_tuple()),
        message=f"not visible within {timeout}s: {locator.by}={locator.value!r} ({locator.layout})",
    )
    return element
