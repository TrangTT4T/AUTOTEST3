"""Dynamic catalogue pages: content that arrives asynchronously (spinner, lazy load, slider).

These pages are where naive tests flake. The patterns used here:
* wait for a STATE (spinner gone AND grid present), never for a fixed time;
* read many elements in ONE evaluate call, so the snapshot cannot tear mid-update;
* for content that keeps changing (the slider), record a HISTORY of changes in the page with
  a MutationObserver and assert on the history, not on a single racy snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import expect

from swaglabs.domain import Money
from swaglabs.pages.base import BasePage

_READ_TILES = """(tiles, s) => tiles.map(tile => {
    const name = tile.querySelector(s.name);
    const price = tile.querySelector(s.price);
    const box = tile.getBoundingClientRect();
    return {
        id: tile.dataset.test,
        name: name ? name.innerText : null,
        price: price ? price.innerText : null,
        loading: tile.querySelector(s.placeholder) !== null,
        on_screen: box.bottom > 0 && box.top < window.innerHeight,
    };
})"""

_RECORD_SHOWN = """(s) => {
    const shown = () => { const el = document.querySelector(s.name); return el ? el.innerText : null; };
    const history = window.__sliderHistory = [shown()];
    new MutationObserver(() => {
        const name = shown();
        if (name !== history[history.length - 1]) history.push(name);
    }).observe(document.querySelector(s.container), {subtree: true, childList: true, characterData: true});
}"""


@dataclass(frozen=True)
class Tile:
    """A product tile on a dynamic page. ``loading`` = still a placeholder."""

    id: str
    name: str | None
    price: Money | None
    loading: bool
    on_screen: bool


def _tiles(rows: list[dict[str, object]]) -> list[Tile]:
    return [
        Tile(
            str(r["id"]),
            None if r["name"] is None else str(r["name"]),
            None if r["price"] is None else Money.parse(str(r["price"])),
            bool(r["loading"]),
            bool(r["on_screen"]),
        )
        for r in rows
    ]


class TiledCatalogPage(BasePage):
    """Common reading of product tiles; subclasses declare ``_container`` and ``_tile``."""

    _container: str
    _tile: str

    def read_tiles(self) -> list[Tile]:
        parts = {"name": self._tile_name, "price": self._tile_price, "placeholder": self._tile_placeholder}
        return _tiles(self.find(self._container).locator(self._tile).evaluate_all(_READ_TILES, parts))

    # --- Locators -------------------------------------------------------------
    _tile_name = "[data-test$='-name']"
    _tile_price = "[data-test$='-price']"
    _tile_placeholder = "[data-test$='-placeholder']"


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


class SliderCatalogPage(BasePage):
    PATH = "/dynamic-catalog-slider.html"

    def wait_until_loaded(self) -> None:
        expect(self.find(self._shown_name)).to_be_visible()

    def snapshot(self) -> tuple[str, str]:
        """(name on show, product the active dot names) - read together, in one call."""
        values = self.page.evaluate(
            "(s) => [document.querySelector(s.name).innerText,"
            " document.querySelector(s.active).getAttribute('aria-label')]",
            {"name": self._shown_name, "active": self._active_dot},
        )
        return str(values[0]), re.sub(r"^Show ", "", str(values[1]))

    def start_recording(self) -> None:
        self.page.evaluate(_RECORD_SHOWN, {"name": self._shown_name, "container": self._container})

    def history(self) -> list[str]:
        return [str(n) for n in self.page.evaluate("() => window.__sliderHistory || []")]

    def pause(self, milliseconds: int) -> None:
        """Sampling cadence for watching the slider over time - NOT a wait for a state."""
        self.page.wait_for_timeout(milliseconds)

    def choose(self, product_name: str) -> None:
        self.find(self._dot.format(name=product_name)).click()

    # --- Locators -------------------------------------------------------------
    _container = "[data-test='dynamic-catalog-slider-container']"
    _shown_name = "[data-test='dynamic-catalog-slider-item-name']"
    _active_dot = "[data-test^='dynamic-catalog-slider-dot-'][aria-current='true']"
    _dot = "role=button[name='Show {name}']"
