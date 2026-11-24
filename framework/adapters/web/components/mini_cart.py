"""Mini-cart: the drawer that opens from the header's "My Cart (N)" link.

Observed behaviour (2026-11-18): the drawer's rows are rendered when the page
loads. After an AJAX Add to Cart the header number updates, but the drawer
stays as it was until the next page load. Tests must load a page after a cart
change before reading the drawer — or report this as a defect.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.components.cart_rows import read_rows, the_only_row
from framework.adapters.web.components.header import Header
from framework.domain import Cart, Catalogue, Money


class MiniCart:
    def __init__(self, page: Page, catalogue: Catalogue) -> None:
        self.page = page
        self._catalogue = catalogue
        self.root = page.locator(self._root)
        self.rows = self.root.locator(self._row).filter(has=page.locator(self._row_title))

    def open(self) -> MiniCart:
        if not self.root.is_visible():
            Header(self.page).cart_link.click()
        expect(self.root).to_be_visible()
        return self

    def is_open(self) -> bool:
        return self.root.is_visible()

    def read(self) -> Cart:
        """Lines as shown in the drawer. The drawer has no total, so it is the sum of the lines."""
        self.open()
        lines = tuple(read_rows(self.rows, self._catalogue))
        return Cart(lines, sum((line.line_total for line in lines), Money.zero()))

    def remove(self, name: str) -> None:
        handle = self._catalogue.by_name(name).handle
        rows = self.rows.filter(has=self.page.locator(self._row_product_link.format(handle=handle)))
        row = the_only_row(rows, name)
        with self.page.expect_response(lambda r: "/cart/change" in r.url):
            row.locator(self._row_remove_link).click()

    # --- Locators -------------------------------------------------------------
    _root = "#drawer"
    # Rows (inside the drawer): a row is a product line when it has a level-3 heading.
    _row = ".row"
    _row_title = "role=heading[level=3]"
    _row_product_link = "h3 a[href$='/products/{handle}']"
    _row_remove_link = "role=link[name='Remove']"
