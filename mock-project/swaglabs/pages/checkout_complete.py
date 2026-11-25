"""Checkout complete (/checkout-complete.html): the confirmation."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header


class CheckoutCompletePage(BasePage):
    PATH = "/checkout-complete.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = Header(page)
        self.heading = self.find(self._heading)

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def expect_heading(self, text: str) -> None:
        expect(self.heading).to_have_text(text)

    # --- Locators -------------------------------------------------------------
    _heading = "[data-test='complete-header']"
