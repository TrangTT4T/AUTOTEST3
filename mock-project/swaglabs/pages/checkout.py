"""Checkout: information (step one), overview (step two) and confirmation pages."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from swaglabs.domain import Money, OrderSummary
from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header


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


class CheckoutOverviewPage(BasePage):
    PATH = "/checkout-step-two.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = Header(page)

    def wait_until_loaded(self) -> None:
        expect(self.find(self._finish)).to_be_visible()

    def item_names(self) -> list[str]:
        return self.find(self._item_name).all_inner_texts()

    def item_prices(self) -> list[Money]:
        return [Money.parse(text) for text in self.find(self._item_price).all_inner_texts()]

    def read_summary(self) -> OrderSummary:
        return OrderSummary(
            subtotal=Money.parse(self.find(self._subtotal).inner_text()),
            tax=Money.parse(self.find(self._tax).inner_text()),
            total=Money.parse(self.find(self._total).inner_text()),
        )

    def finish(self) -> None:
        self.find(self._finish).click()

    # --- Locators -------------------------------------------------------------
    _item_name = "[data-test='cart-list'] [data-test='inventory-item-name']"
    _item_price = "[data-test='cart-list'] [data-test='inventory-item-price']"
    _subtotal = "[data-test='subtotal-label']"
    _tax = "[data-test='tax-label']"
    _total = "[data-test='total-label']"
    _finish = "[data-test='finish']"


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
