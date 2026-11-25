"""Dynamic catalogue that loads tiles as they scroll into view: /dynamic-catalog-lazy-load.html."""

from __future__ import annotations

from playwright.sync_api import expect

from swaglabs.pages.tiled_catalog import TiledCatalogPage


class LazyLoadCatalogPage(TiledCatalogPage):
    PATH = "/dynamic-catalog-lazy-load.html"

    def wait_until_loaded(self) -> None:
        expect(self.find(self._container)).to_be_visible()

    def scroll_one_screen(self) -> None:
        """Scroll down by one screen, like a reader. Tiles load only once they are ON SCREEN, so
        jumping straight to the end would skip the tiles in between and leave them placeholders."""
        self.find(self._container).evaluate("() => window.scrollBy(0, window.innerHeight)")

    # --- Locators -------------------------------------------------------------
    _container = "[data-test='dynamic-catalog-lazy-load-container']"
    _tile = ".dynamic_catalog_card"
