"""Checkout step two (/checkout-step-two.html): the order summary before finishing."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from swaglabs.domain import Money, OrderSummary
from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header


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
