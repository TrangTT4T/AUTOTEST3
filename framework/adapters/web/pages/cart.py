"""Cart page: /cart.

Two testability problems shape this file:
* every page also contains a HIDDEN mini-cart with the same rows and
  duplicate element ids, so all row locators are scoped to ``#cart``;
* the quantity box has no label, so it is found inside one product's row.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.adapters.web.components.cart_rows import read_rows
from framework.adapters.web.pages.base import BasePage
from framework.domain import Cart, Catalogue, Money


class CartPage(BasePage):
    PATH = "/cart"

    def __init__(self, page: Page, catalogue: Catalogue) -> None:
        super().__init__(page)
        self._catalogue = catalogue
        self.root = self.find(self._root)
        self.heading = self.find(self._heading)
        self.empty_message = self.find(self._empty_message)
        self.total = self.find(self._total)
        self.note = self.find(self._note)
        self.continue_shopping_link = self.find(self._continue_shopping_link)
        self.update_button = self.find(self._update_button)
        self.checkout_button = self.find(self._checkout_button)

    def open(self) -> CartPage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()  # shown for empty and filled carts

    # --- reading -------------------------------------------------------------
    def _rows(self) -> Locator:
        return self.root.locator(self._row).filter(has=self.find(self._row_title))

    def _rows_for(self, name: str) -> Locator:
        handle = self._catalogue.by_name(name).handle
        return self._rows().filter(has=self.find(self._row_product_link.format(handle=handle)))

    def is_empty(self) -> bool:
        return self.empty_message.is_visible()

    def read(self) -> Cart:
        if self.is_empty():
            return Cart.empty()
        lines = tuple(read_rows(self._rows(), self._catalogue))
        return Cart(lines, Money.parse(self.total.inner_text()))

    def header_count(self) -> int:
        return self.header.cart_count()

    # --- changing ------------------------------------------------------------
    def set_quantity(self, name: str, quantity: int) -> None:
        self._rows_for(name).first.locator(self._row_quantity).fill(str(quantity))
        with self.page.expect_response(lambda r: r.url.endswith("/cart") and r.request.method == "POST"):
            self.update_button.click()

    def remove_all(self, name: str) -> None:
        """Remove every row (variant) of one product."""
        while self._rows_for(name).count() > 0:
            with self.page.expect_response(lambda r: "/cart/change" in r.url):
                self._rows_for(name).first.locator(self._row_remove_link).click()
            self.open()

    def continue_shopping(self) -> None:
        self.continue_shopping_link.click()
        self.page.wait_for_url("**/collections/all")

    def check_out(self) -> None:
        self.checkout_button.click()

    # --- Locators -------------------------------------------------------------
    _root = "#cart"
    _heading = "role=heading[level=1][name='My Cart']"
    _empty_message = "text=It appears that your cart is currently empty!"
    _total = "role=heading[level=2][name=/^Total /]"
    _note = "role=textbox[name='Add a note to your order...']"
    # "« Continue Shopping" under a filled cart, "Continue Shopping" in the empty message.
    _continue_shopping_link = "role=link[name=/Continue Shopping$/]"
    _update_button = "role=button[name='Update']"
    _checkout_button = "role=button[name='Check Out']"
    # Rows (inside _root): a row is a product line when it has a level-3 heading.
    _row = ".row"
    _row_title = "role=heading[level=3]"
    _row_product_link = "h3 a[href$='/products/{handle}']"
    _row_quantity = "input[name='updates[]']"
    _row_remove_link = "role=link[name='x']"
