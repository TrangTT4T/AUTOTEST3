"""Product page: /inventory-item.html?id=<id>."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, expect

from swaglabs.domain import Money
from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header
from swaglabs.pages.inventory import Card


class ProductPage(BasePage):
    PATH = "/inventory-item.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = Header(page)
        self.back_button = self.find(self._back)
        self.name = self.find(self._name)

    def wait_until_loaded(self) -> None:
        # The URL changes before the SPA has replaced the catalogue: wait for an element that
        # only exists on this page, or reads would still see the catalogue's cards.
        self.page.wait_for_url(f"**{self.PATH}?id=*")
        expect(self.back_button).to_be_visible()

    def product_id(self) -> int:
        return int(parse_qs(urlsplit(self.page.url).query)["id"][0])

    def expect_name(self, name: str) -> None:
        expect(self.name).to_have_text(name)

    def read(self) -> Card:
        return Card(
            self.name.inner_text(),
            Money.parse(self.find(self._price).inner_text()),
            self.find(self._image).get_attribute("src") or "",
        )

    def back_to_products(self) -> None:
        self.back_button.click()

    # --- Locators -------------------------------------------------------------
    _back = "[data-test='back-to-products']"
    _name = "[data-test='inventory-item-name']"
    _price = "[data-test='inventory-item-price']"
    _image = "img.inventory_details_img"
