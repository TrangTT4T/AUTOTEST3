"""Checkout step 1: the shipping address.

A demo app: completing the order charges nothing, so - unlike the web shop - the whole checkout
may be automated.
"""

from __future__ import annotations

from framework.adapters.mobile.forms import Address
from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen


class ShippingScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._heading)

    def is_current(self) -> bool:
        return self.is_shown(self._heading)

    def submit(self, address: Address) -> None:
        self.wait_until_loaded()
        for locator, value in (
            (self._full_name, address.full_name),
            (self._address_1, address.line_1),
            (self._address_2, address.line_2),
            (self._city, address.city),
            (self._state, address.state),
            (self._zip, address.zip_code),
            (self._country, address.country),
        ):
            if value:
                self.type_into(locator, value)
        self.tap(self._to_payment)

    # --- Locators -----------------------------------------------------------------
    _heading = by_id("enterShippingAddressTV", "fragment_checkout_info")
    _full_name = by_id("fullNameET", "fragment_checkout_info")
    _address_1 = by_id("address1ET", "fragment_checkout_info")
    _address_2 = by_id("address2ET", "fragment_checkout_info")
    _city = by_id("cityET", "fragment_checkout_info")
    _state = by_id("stateET", "fragment_checkout_info")
    _zip = by_id("zipET", "fragment_checkout_info")
    _country = by_id("countryET", "fragment_checkout_info")
    _to_payment = by_accessibility_id("Saves user info for checkout", "fragment_checkout_info")
