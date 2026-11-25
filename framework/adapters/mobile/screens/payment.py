"""Checkout step 2: the payment card."""

from __future__ import annotations

from framework.adapters.mobile.forms import Card
from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen


class PaymentScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._heading)

    def submit(self, card: Card) -> None:
        self.wait_until_loaded()
        self.type_into(self._name, card.holder)
        self.type_into(self._card_number, card.number)
        self.type_into(self._expiry, card.expiry)
        self.type_into(self._security_code, card.security_code)
        self.tap(self._review)

    # --- Locators -----------------------------------------------------------------
    _heading = by_id("enterPaymentMethodTV", "fragment_checkout")
    _name = by_id("nameET", "fragment_checkout")
    _card_number = by_id("cardNumberET", "fragment_checkout")
    _expiry = by_id("expirationDateET", "fragment_checkout")
    _security_code = by_id("securityCodeET", "fragment_checkout")
    _review = by_accessibility_id(
        "Saves payment info and launches screen to review checkout data", "fragment_checkout"
    )
