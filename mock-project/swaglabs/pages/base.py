"""Base page object: a "loaded" contract, verified input, and the header shared by inner pages."""

from __future__ import annotations

from typing import ClassVar, Self

from playwright.sync_api import Locator, Page, expect

# Typing into a field is synchronous in the browser: if the value is not there almost at once,
# it will never be. A short, explicit timeout keeps a lost keystroke from costing a full UI timeout.
INPUT_SETTLE_MS = 2000


class BasePage:
    """A page object owns the selectors and the waits of one page.

    Rules (enforced by tests/unit/test_architecture.py):
    * selectors are string constants in the ``# --- Locators ---`` section at the BOTTOM of the
      class, used through ``find`` - never inline in a method;
    * ``open`` returns only when ``wait_until_loaded`` proves the page is usable;
    * methods speak business language (``add(product)``) and return domain values.
    """

    PATH: ClassVar[str] = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def find(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def open(self) -> Self:
        self.page.goto(self.PATH)
        self.wait_until_loaded()
        return self

    def wait_until_loaded(self) -> None:
        """Override: wait for the element that proves this page is ready."""
        raise NotImplementedError

    def fill_verified(self, field: Locator, value: str) -> None:
        """Type ``value`` and check the field really holds it.

        Catches inputs that drop or redirect keystrokes - a defect class that a plain
        ``fill`` hides until a later, confusing failure.
        """
        field.fill(value)
        expect(field, f"the field should keep the text {value!r}").to_have_value(
            value, timeout=INPUT_SETTLE_MS
        )
