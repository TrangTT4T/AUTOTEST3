"""Checkout step one (/checkout-step-one.html): the buyer's details."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from swaglabs.pages.base import BasePage


class CheckoutInfoPage(BasePage):
    PATH = "/checkout-step-one.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.first_name = self.find(self._first_name)
        self.last_name = self.find(self._last_name)
        self.postal_code = self.find(self._postal_code)
        self.error = self.find(self._error)

    def wait_until_loaded(self) -> None:
        expect(self.find(self._continue)).to_be_visible()

    def enter_details(self, first_name: str, last_name: str, postal_code: str) -> None:
        """Type the non-empty values, each verified; an empty value means "leave the field empty"."""
        for field, value in (
            (self.first_name, first_name),
            (self.last_name, last_name),
            (self.postal_code, postal_code),
        ):
            if value:
                self.fill_verified(field, value)

    def continue_(self) -> None:
        self.find(self._continue).click()

    def expect_error(self, message: str) -> None:
        expect(self.error).to_have_text(message)

    # --- Locators -------------------------------------------------------------
    _first_name = "[data-test='firstName']"
    _last_name = "[data-test='lastName']"
    _postal_code = "[data-test='postalCode']"
    _continue = "[data-test='continue']"
    _error = "[data-test='error']"
