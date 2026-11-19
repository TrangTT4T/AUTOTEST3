"""Home page: /. Shows the featured products ("frontpage" collection)."""

from __future__ import annotations

from playwright.sync_api import expect

from framework.adapters.web.components import ProductGrid
from framework.adapters.web.pages.base import BasePage
from framework.domain import ProductCard


class HomePage(BasePage):
    PATH = "/"

    def open(self) -> HomePage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.header.search_box).to_be_visible()

    def featured_products(self) -> list[ProductCard]:
        return ProductGrid(self.page).read()
