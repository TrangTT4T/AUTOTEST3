"""Login and the three checkout screens, then the confirmation.

A demo app: completing the order charges nothing, so — unlike the web shop —
the whole checkout may be automated.
"""

from __future__ import annotations

from dataclasses import dataclass

from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen, number
from framework.domain import Money


class LoginScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._submit)

    def log_in(self, username: str, password: str) -> None:
        self.wait_until_loaded()
        self.type_into(self._username, username)
        self.type_into(self._password, password)
        self.tap(self._submit)

    def password_error(self) -> str:
        return self.visible(self._password_error).text.strip()

    def username_error(self) -> str:
        return self.visible(self._username_error).text.strip()

    # --- Locators -----------------------------------------------------------------
    _title = by_id("loginTV", "fragment_login")
    _username = by_id("nameET", "fragment_login")
    _password = by_id("passwordET", "fragment_login")
    _submit = by_accessibility_id("Tap to login with given credentials", "fragment_login")
    _username_error = by_id("nameErrorTV", "fragment_login")
    _password_error = by_id("passwordErrorTV", "fragment_login")  # also shows "locked out"


@dataclass(frozen=True)
class Address:
    full_name: str
    line_1: str
    city: str
    zip_code: str
    country: str
    line_2: str = ""
    state: str = ""


@dataclass(frozen=True)
class Card:
    holder: str
    number: str
    expiry: str  # MM/YY
    security_code: str


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


class CompleteScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._title)

    def title(self) -> str:
        return self.visible(self._title).text.strip()

    def continue_shopping(self) -> None:
        self.tap(self._continue)

    # --- Locators -----------------------------------------------------------------
    _title = by_id("completeTV", "fragment_checkout_complete")  # "Checkout Complete"
    _continue = by_accessibility_id("Tap to open catalog", "fragment_checkout_complete")
