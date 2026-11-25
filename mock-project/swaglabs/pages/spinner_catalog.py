"""Dynamic catalogue with a loading spinner: /dynamic-catalog-spinner.html."""

from __future__ import annotations

from playwright.sync_api import expect

from swaglabs.pages.tiled_catalog import TiledCatalogPage


class SpinnerCatalogPage(TiledCatalogPage):
    PATH = "/dynamic-catalog-spinner.html"

    def wait_until_loaded(self) -> None:
        expect(self.find(self._container)).to_be_visible()

    def wait_for_products(self) -> None:
        expect(self.find(self._spinner), "the spinner should go away").to_be_hidden()
        expect(self.find(self._grid)).to_be_visible()

    # --- Locators -------------------------------------------------------------
    _container = "[data-test='dynamic-catalog-spinner-container']"
    _spinner = "role=status[name='Loading']"
    _grid = "[data-test='dynamic-catalog-spinner-grid']"
    _tile = ".dynamic_catalog_card"  # a tile's data-test is per index (spinner-item-3): use its class
