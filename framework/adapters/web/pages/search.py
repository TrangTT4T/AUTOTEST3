"""Search results page: /search?q=..."""

from __future__ import annotations

from urllib.parse import quote_plus

from playwright.sync_api import Page, expect

from framework.adapters.web.components import ProductGrid
from framework.adapters.web.pages.base import BasePage
from framework.domain import ProductCard


class SearchResultsPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = self.find(self._heading)
        self.no_results_message = self.find(self._no_results_message)
        self.grid = ProductGrid(page)

    def open_for(self, keyword: str) -> SearchResultsPage:
        """Open results directly by URL (faster than typing; use Header.search to test the box)."""
        return self.open_path(f"/search?type=product&q={quote_plus(keyword)}")

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def results(self) -> list[ProductCard]:
        self.wait_until_loaded()
        return self.grid.read()

    def titles(self) -> list[str]:
        return [card.name for card in self.results()]

    def open_result(self, name: str) -> None:
        self.grid.open(name)

    def has_no_results(self) -> bool:
        self.wait_until_loaded()
        return self.no_results_message.is_visible()

    def keyword_message(self) -> str:
        """The line above the results, e.g. 'Showing results for jacket'."""
        self.wait_until_loaded()
        return " ".join(self.find(self._keyword_message).inner_text().split())

    # --- Locators -------------------------------------------------------------
    _heading = "role=heading[name='Search Results']"
    _no_results_message = "text=No results found for"
    _keyword_message = "#keyword"
