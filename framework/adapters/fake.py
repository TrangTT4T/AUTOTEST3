"""In-memory Store adapter: fast, offline, deterministic.

It is fed by a recorded snapshot of the real catalogue, so fake and live
runs use the same product names, prices, variants, and sold-out status.
Content the catalogue does not contain (menu page titles, the blog article,
the 404 page) mirrors what was observed on the live shop on 2026-11-18.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from framework.domain import Cart, CartLine, Catalogue, Money, OrderSummary, Product, ProductCard
from framework.errors import AmbiguousTargetError

DATA = Path(__file__).resolve().parents[2] / "tests" / "data"
DEFAULT_SNAPSHOT = DATA / "catalogue_snapshot.json"  # the web shop (GBP)
MOBILE_SNAPSHOT = DATA / "mobile_catalogue.json"  # My Demo App (USD), extracted from its source


class FakeStore:
    # The live titles use an EN DASH (U+2013), written as an escape so it is visible.
    MENU_PAGES: ClassVar[Mapping[str, str]] = MappingProxyType(
        {"About Us": "About Us \u2013 Sauce Demo", "Blog": "News \u2013 Sauce Demo"}
    )
    LATEST_ARTICLE = "First Post"
    NOT_FOUND_TITLE = "404 Not Found \u2013 Sauce Demo"

    def __init__(self, catalogue: Catalogue) -> None:
        self._catalogue = catalogue
        self._lines: dict[tuple[str, str], int] = {}  # (product, variant) -> quantity
        self._at_checkout = False

    @classmethod
    def from_snapshot(cls, path: Path = DEFAULT_SNAPSHOT) -> FakeStore:
        return cls(Catalogue.from_products_json(json.loads(path.read_text(encoding="utf-8"))))

    # --- catalogue -------------------------------------------------------
    def open_product(self, name: str) -> Product:
        item = self._catalogue.by_name(name)
        return Product(item.name, item.price, item.available)

    def catalogue_price(self, name: str) -> Money:
        return self._catalogue.by_name(name).price

    def catalogue_data(self) -> Catalogue:
        return self._catalogue

    def catalogue_listing(self) -> list[ProductCard]:
        return [
            ProductCard(item.name, item.price, not item.available, item.handle)
            for item in (self._catalogue.by_name(n) for n in self._catalogue.names())
        ]

    def find_sold_out_product(self) -> str | None:
        sold_out = self._catalogue.sold_out()
        return sold_out[0].name if sold_out else None

    def search(self, keyword: str) -> list[str]:
        return [n for n in self._catalogue.names() if keyword.lower() in n.lower()]

    # --- cart ------------------------------------------------------------
    def add(self, name: str, quantity: int = 1) -> None:
        variant = self._catalogue.by_name(name).first_available_variant()
        self._add_line(name, variant.title, quantity)

    def add_variant(self, name: str, variant: str, quantity: int = 1) -> None:
        self._catalogue.by_name(name).variant(variant)  # raises if it does not exist
        self._add_line(name, variant, quantity)

    def _add_line(self, name: str, variant: str, quantity: int) -> None:
        key = (name, variant)
        self._lines[key] = self._lines.get(key, 0) + quantity

    def try_add(self, name: str) -> bool:
        if not self._catalogue.by_name(name).available:
            return False
        self.add(name)
        return True

    def prefill(self, items: Mapping[str, int]) -> None:
        for name, quantity in items.items():
            self.add(name, quantity)

    def set_quantity(self, name: str, quantity: int) -> None:
        keys = [key for key in self._lines if key[0] == name]
        if len(keys) != 1:  # same rule as the web cart: one line, or the request is ambiguous
            raise AmbiguousTargetError(
                f"{name!r} has {len(keys)} lines in the cart; this action needs exactly one "
                "(with several variants, address one variant)"
            )
        if quantity <= 0:  # like Shopify: quantity 0 removes the line
            del self._lines[keys[0]]
        else:
            self._lines[keys[0]] = quantity

    def remove(self, name: str) -> None:
        for key in [key for key in self._lines if key[0] == name]:
            del self._lines[key]

    def cart(self) -> Cart:
        self._at_checkout = False
        lines = tuple(
            CartLine(name, variant, qty, self._catalogue.by_name(name).variant(variant).price * qty)
            for (name, variant), qty in self._lines.items()
        )
        return Cart(lines, sum((line.line_total for line in lines), Money.zero(self._catalogue.currency)))

    # --- navigation ------------------------------------------------------
    def go_to_checkout(self) -> str:
        self._at_checkout = bool(self._lines)
        return "Checkout - Sauce Demo" if self._lines else "Your Shopping Cart"

    def checkout_summary(self) -> OrderSummary:
        cart = self.cart()
        # UK prices include 20% VAT: tax = total / 6.
        return OrderSummary(cart.lines, cart.total, cart.total, Money(cart.total.amount / 6))

    def open_menu_page(self, link: str) -> str:
        return self.MENU_PAGES[link]

    def open_latest_article(self) -> tuple[str, str]:
        return self.LATEST_ARTICLE, self.LATEST_ARTICLE

    def open_missing_page(self) -> tuple[int | None, str]:
        return 404, self.NOT_FOUND_TITLE
