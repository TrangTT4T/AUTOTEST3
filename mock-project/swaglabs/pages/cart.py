"""Cart page: /cart.html."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from swaglabs.domain import Cart, CartLine, Money, Product
from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header


class CartPage(BasePage):
    PATH = "/cart.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = Header(page)
        self.list = self.find(self._list)

    def wait_until_loaded(self) -> None:
        expect(self.find(self._checkout)).to_be_visible()

    def read(self) -> Cart:
        selectors = {"name": self._line_name, "quantity": self._line_quantity, "price": self._line_price}
        rows = self.list.locator(self._line).evaluate_all(self._read_lines_js, selectors)
        return Cart.of(CartLine(r["name"], int(r["quantity"]), Money.parse(r["price"])) for r in rows)

    def expect_names(self, names: list[str]) -> None:
        expect(self.list.locator(self._line_name)).to_have_text(names)

    def remove(self, product: Product) -> None:
        self.find(self._remove.format(slug=product.slug)).click()

    def check_out(self) -> None:
        self.find(self._checkout).click()

    # --- Locators -------------------------------------------------------------
    _list = "[data-test='cart-list']"
    _line = "[data-test='inventory-item']"
    _line_name = "[data-test='inventory-item-name']"
    _line_quantity = "[data-test='item-quantity']"
    _line_price = "[data-test='inventory-item-price']"
    _remove = "[data-test='remove-{slug}']"
    _checkout = "[data-test='checkout']"

    # --- Scripts (run in the page) --------------------------------------------
    # One round trip reads every line at once: a consistent snapshot.
    _read_lines_js = """(lines, s) => lines.map(line => ({
        name: line.querySelector(s.name).innerText,
        quantity: line.querySelector(s.quantity).innerText,
        price: line.querySelector(s.price).innerText,
    }))"""
