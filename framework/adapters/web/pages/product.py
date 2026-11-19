"""Product page: /products/<handle>."""

from __future__ import annotations

from playwright.sync_api import Page, Response, expect

from framework.adapters.web.pages.base import BasePage
from framework.domain import CatalogueItem, Money, Product, Variant


class ProductPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.title = self.find(self._title)
        self.price = self.find(self._price)
        self.add_button = self.find(self._add_to_cart_button)
        self.sold_out_button = self.find(self._sold_out_button)
        self.option_selects = self.find(self._option_selects)
        self.selected_variant_id = self.find(self._selected_variant_id)

    def open_for(self, item: CatalogueItem) -> ProductPage:
        # URLs come from catalogue data, never from names:
        # "Black heels" lives at /products/flower-print-jeans.
        self.open_path(f"/products/{item.handle}")
        expect(self.title).to_have_text(item.name)
        return self

    def wait_until_loaded(self) -> None:
        expect(self.title).to_be_visible()

    def read(self) -> Product:
        return Product(
            name=self.title.inner_text().strip(),
            price=Money.parse(self.price.inner_text()),
            available=self.add_button.is_visible(),
        )

    def option_names(self) -> list[str]:
        """Labels of the option boxes, e.g. ['Size', 'Color']. Empty for one-variant products."""
        return [
            (
                select.get_attribute("aria-label") or select.evaluate("e => e.labels[0]?.innerText || ''")
            ).strip()
            for select in self.option_selects.all()
        ]

    def select_variant(self, variant: Variant) -> None:
        """Choose a variant through the option boxes, then prove the page picked the right id.

        Variant titles list option values in option order: "L / Red" = Size L, Color Red.
        """
        values = variant.title.split(" / ")
        selects = self.option_selects.all()
        if len(selects) != len(values):
            raise AssertionError(f"{len(selects)} option boxes for variant {variant.title!r}")
        for select, value in zip(selects, values, strict=True):
            select.select_option(value)
        expect(self.selected_variant_id).to_have_value(str(variant.id))

    def add_to_cart(self, times: int = 1) -> None:
        """Click Add to Cart and wait for the server to confirm every click.

        Add to Cart is AJAX. A load-state wait (e.g. "networkidle") returns
        at once on an already-loaded page, so it cannot prove the add finished.
        """
        for _ in range(times):
            response = self.click_add_to_cart()
            if not response.ok:
                raise AssertionError(f"add to cart failed: HTTP {response.status}")

    def click_add_to_cart(self) -> Response:
        """Click once and return the server's answer, whatever it is (for error-handling tests)."""
        with self.page.expect_response(lambda r: "/cart/add" in r.url) as response:
            self.add_button.click()
        return response.value

    def is_sold_out(self) -> bool:
        if not self.sold_out_button.is_visible():
            return False
        expect(self.sold_out_button).to_be_disabled()
        return True

    # --- Locators -------------------------------------------------------------
    # itemprop="name" is schema.org markup: themes keep it for search engines,
    # and it avoids the shop's other <h1> (the logo).
    _title = "[itemprop='name']"
    _price = "#product-price"
    _add_to_cart_button = "role=button[name='Add to Cart']"
    _sold_out_button = "role=button[name='Sold Out']"
    # One visible <select> per option (Size, Color, ...). The theme copies the
    # choice into a hidden <select name="id"> holding the variant id that is sent.
    _option_selects = "#product-variants select.single-option-selector"
    _selected_variant_id = "#product-select"
