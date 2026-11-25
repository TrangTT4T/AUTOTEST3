"""Base page for the dynamic catalogues whose products arrive as tiles (spinner, lazy load).

These pages are where naive tests flake. The patterns used here and in the subclasses:
* wait for a STATE (spinner gone AND grid present), never for a fixed time;
* read many elements in ONE evaluate call, so the snapshot cannot tear mid-update.
"""

from __future__ import annotations

from swaglabs.domain import Money, Tile
from swaglabs.pages.base import BasePage


class TiledCatalogPage(BasePage):
    """Common reading of product tiles; subclasses declare ``_container`` and ``_tile``."""

    _container: str
    _tile: str

    def read_tiles(self) -> list[Tile]:
        parts = {"name": self._tile_name, "price": self._tile_price, "placeholder": self._tile_placeholder}
        rows = self.find(self._container).locator(self._tile).evaluate_all(self._read_tiles_js, parts)
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

    # --- Locators -------------------------------------------------------------
    _tile_name = "[data-test$='-name']"
    _tile_price = "[data-test$='-price']"
    _tile_placeholder = "[data-test$='-placeholder']"

    # --- Scripts (run in the page) --------------------------------------------
    _read_tiles_js = """(tiles, s) => tiles.map(tile => {
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
