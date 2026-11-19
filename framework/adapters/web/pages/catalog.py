"""Catalogue page: /collections/all. Every product, with "Sold Out" labels."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.components import ProductGrid
from framework.adapters.web.pages.base import BasePage
from framework.domain import ProductCard


class CatalogPage(BasePage):
    PATH = "/collections/all"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = self.find(self._heading)
        self.grid = ProductGrid(page)

    def open(self) -> CatalogPage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def products(self) -> list[ProductCard]:
        return self.grid.read()

    def open_product(self, name: str) -> None:
        self.grid.open(name)

    # --- Locators -------------------------------------------------------------
    _heading = "role=heading[level=1][name='Products']"
