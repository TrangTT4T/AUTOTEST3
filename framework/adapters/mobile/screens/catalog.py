"""Catalogue: the product list shown after the splash screen."""

from __future__ import annotations

from selenium.webdriver.remote.webelement import WebElement

from framework.adapters.mobile.locators import by_id
from framework.adapters.mobile.screens.base import Screen


class CatalogScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._list)
        title = self.visible(self._title)
        if title.text.strip() != "Products":
            raise AssertionError(f"expected the catalogue, got {title.text!r}")

    def is_current(self) -> bool:
        titles = [e for e in self.driver.find_elements(*self._title.as_tuple()) if e.is_displayed()]
        return self.is_shown(self._list) and any(t.text.strip() == "Products" for t in titles)

    def _tile_title(self, name: str) -> WebElement | None:
        for title in self.driver.find_elements(*self._item_title.as_tuple()):
            if title.text.strip() == name and title.is_displayed():
                return title
        return None

    def open_product(self, name: str) -> None:
        self.wait_until_loaded()
        found = self.scroll_until(lambda: self._tile_title(name) is not None, self._scroll)
        tile = self._tile_title(name)
        if not found or tile is None:
            raise AssertionError(f"product {name!r} not found in the catalogue")
        tile.click()

    # --- Locators -----------------------------------------------------------------
    _title = by_id("productTV", "fragment_product_catalog")  # text "Products"
    _list = by_id("productRV", "fragment_product_catalog")
    _scroll = by_id("scrollView", "fragment_product_catalog")
    _item_title = by_id("titleTV", "item_products")
    _item_price = by_id("priceTV", "item_products")
