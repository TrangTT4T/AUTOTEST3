"""Checkout step 3: review the order and place it."""

from __future__ import annotations

from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen, number
from framework.domain import Money


class ReviewScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._place_order)

    def item_count(self) -> int:
        return number(self.visible(self._items).text)

    def delivery(self) -> Money:
        return Money.parse(self.visible(self._delivery).text, "USD")

    def total(self) -> Money:
        return Money.parse(self.visible(self._total).text, "USD")

    def place_order(self) -> None:
        self.tap(self._place_order)

    # --- Locators -----------------------------------------------------------------
    _heading = by_id("enterShippingAddressTV", "fragment_place_order")  # text "Review your order"
    _items = by_id("itemNumberTV", "fragment_place_order")  # "<n> Items"
    _delivery = by_id("amountTV", "fragment_place_order")  # "$5.99"
    _total = by_id("totalAmountTV", "fragment_place_order")  # "$ 65.97"
    _place_order = by_accessibility_id("Completes the process of checkout", "fragment_place_order")
