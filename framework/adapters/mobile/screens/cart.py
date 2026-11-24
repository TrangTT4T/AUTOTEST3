"""Cart: lines, quantities, total, remove, checkout."""

from __future__ import annotations

from selenium.webdriver.remote.webelement import WebElement

from framework.adapters.mobile.locators import by_accessibility_id, by_id, by_xpath
from framework.adapters.mobile.screens.base import Screen, number
from framework.adapters.mobile.waits import wait_until
from framework.domain import Cart, CartLine, Money
from framework.errors import AmbiguousTargetError


class CartScreen(Screen):
    def wait_until_loaded(self) -> None:
        """Either state proves the cart is shown: the total, or the empty state ("No Items")."""
        wait_until(
            lambda: self.is_shown(self._total) or self.is_shown(self._empty_title),
            bool,
            timeout=self.timeout,
        )

    def is_empty(self) -> bool:
        return self.is_shown(self._empty_title)

    def _rows(self) -> list[WebElement]:
        """Each cart line is the parent of a line title; resolved through its children."""
        return [t for t in self.driver.find_elements(*self._line_title.as_tuple()) if t.is_displayed()]

    def _row_of(self, title: WebElement) -> WebElement:
        return title.find_element(*self._line_row_from_title.as_tuple())

    def read(self) -> Cart:
        self.wait_until_loaded()
        if self.is_empty():
            return Cart.empty("USD")
        lines = []
        for title in self._rows():
            row = self._row_of(title)
            quantity = number(self.one(self._line_quantity, within=row).text)
            price = Money.parse(self.one(self._line_price, within=row).text, "USD")
            lines.append(CartLine(title.text.strip(), "", quantity, price * quantity))
        total = Money.parse(self.visible(self._total).text, "USD")
        return Cart(tuple(lines), total)

    def items_label(self) -> int:
        return number(self.visible(self._items).text)

    def _row_for(self, name: str) -> WebElement:
        """The single line of ``name``: several lines (e.g. two colours) or none are ambiguous.

        Not the first match: that would silently act on one line and leave the others; and not an
        AssertionError, which this project reserves for product defects.
        """
        titles = [title for title in self._rows() if title.text.strip() == name]
        if len(titles) != 1:
            raise AmbiguousTargetError(f"{name!r} has {len(titles)} lines in the cart; expected exactly one")
        return self._row_of(titles[0])

    def remove(self, name: str) -> None:
        before = self.cart_count()
        row = self._row_for(name)
        quantity = number(self.one(self._line_quantity, within=row).text)
        self.one(self._line_remove, within=row).click()
        self.wait_for_cart_count(before - quantity)

    def set_quantity(self, name: str, quantity: int) -> None:
        for _ in range(20):
            row = self._row_for(name)
            current = number(self.one(self._line_quantity, within=row).text)
            if current == quantity:
                return
            before = self.cart_count()
            self.one(self._line_plus if current < quantity else self._line_minus, within=row).click()
            self.wait_for_cart_count(before + (1 if current < quantity else -1))
        raise AssertionError(f"could not set {name!r} to {quantity}")

    def proceed_to_checkout(self) -> None:
        self.tap(self._checkout)

    def go_shopping(self) -> None:
        self.tap(self._go_shopping)

    # --- Locators -----------------------------------------------------------------
    _title = by_id("productTV", "fragment_cart")  # text "My Cart"
    _list = by_id("productRV", "fragment_cart")
    _empty_title = by_id("noItemTitleTV", "fragment_cart")  # text "No Items"
    _go_shopping = by_id("shoppingBt", "fragment_cart")
    _items = by_id("itemsTV", "fragment_cart")  # "<n> items"
    _total = by_id("totalPriceTV", "fragment_cart")  # "$ 45.97"
    _checkout = by_accessibility_id("Confirms products for checkout", "fragment_cart")
    # One cart line (item_my_cart):
    _line_title = by_id("titleTV", "item_my_cart")
    _line_price = by_id("priceTV", "item_my_cart")
    _line_quantity = by_id("noTV", "item_my_cart")
    _line_plus = by_accessibility_id("Increase item quantity", "item_my_cart")
    _line_minus = by_accessibility_id("Decrease item quantity", "item_my_cart")
    _line_remove = by_accessibility_id("Removes product from cart", "item_my_cart")
    # From a line's title up to its row: the nearest ancestor that contains the remove button.
    _line_row_from_title = by_xpath(
        "./ancestor::*[.//*[contains(@resource-id, 'removeBt')]][1]", "item_my_cart"
    )
