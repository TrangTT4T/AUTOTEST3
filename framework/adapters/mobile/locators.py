"""How a screen object declares its Android locators (Day 9, Part 3; Day 11).

Each screen class lists its locators at the BOTTOM of the class, after the methods
that use them, in a ``# --- Locators ---`` section (the same convention as the web
page objects). Methods refer to them by name only. This module provides the
``Locator`` type and the three ways to build one.

Every locator names the layout it comes from. ``tests/unit/test_mobile.py`` checks
each one against ``tests/data/mobile_ui_inventory.json``, which was extracted from the
app's source (tools/extract_ui_inventory.py). That catches typos and renamed ids
without a device; behaviour still has to be confirmed on one.

Strategy: accessibility id where the app has a unique content description, resource id
otherwise. No ``-android uiautomator`` (deprecated by Google). XPath appears once,
scoped: in ``CartScreen`` to climb from a line's title to its row.
"""

from __future__ import annotations

from dataclasses import dataclass

from appium.webdriver.common.appiumby import AppiumBy


@dataclass(frozen=True)
class Locator:
    by: str
    value: str
    layout: str  # source layout file (without .xml) the element is defined in

    def as_tuple(self) -> tuple[str, str]:
        return (self.by, self.value)


def by_id(value: str, layout: str) -> Locator:
    """A resource id, e.g. ``cartTV`` (the driver adds the package prefix)."""
    return Locator(AppiumBy.ID, value, layout)


def by_accessibility_id(value: str, layout: str) -> Locator:
    """A content description, e.g. ``"View cart"``."""
    return Locator(AppiumBy.ACCESSIBILITY_ID, value, layout)


def by_xpath(value: str, layout: str) -> Locator:
    """Only for structure that ids cannot express; always relative to a found element."""
    return Locator(AppiumBy.XPATH, value, layout)
