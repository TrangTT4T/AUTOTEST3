"""Store adapter for My Demo App (Android), driven by Appium.

Implements the same port as FakeStore and WebStore, so the Unit 1 cart scenarios
run unchanged (features/mobile_cart.feature). The app is a different product:
no search, no sold-out items, no information pages; those port methods raise
``NotSupportedOnPlatformError`` and no mobile scenario uses them.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from appium.webdriver.webdriver import WebDriver

from framework.adapters.mobile.screens import CartScreen, CatalogScreen, ProductScreen
from framework.adapters.mobile.screens.base import Screen
from framework.domain import Cart, Catalogue, Money, OrderSummary, Product, ProductCard
from framework.errors import CartInconsistencyError, NotSupportedOnPlatformError

log = logging.getLogger("shop.mobile")


class MobileStore:
    def __init__(self, driver: WebDriver, catalogue: Catalogue, timeout: float = 15.0) -> None:
        self.driver = driver
        self.catalogue = catalogue
        self.timeout = timeout
        self._open_product: str | None = None

    # --- navigation helpers -----------------------------------------------------------
    def _to_catalog(self) -> CatalogScreen:
        catalog = CatalogScreen(self.driver, self.timeout)
        cart = CartScreen(self.driver, self.timeout)
        for _ in range(4):
            if catalog.is_current():
                return catalog
            if cart.is_empty():
                cart.go_shopping()
            else:
                Screen(self.driver, self.timeout).back()
        catalog.wait_until_loaded()
        return catalog

    def _on_product(self, name: str) -> ProductScreen:
        if self._open_product != name:
            self.open_product(name)
        return ProductScreen(self.driver, self.timeout)

    def _cart_screen(self) -> CartScreen:
        self._open_product = None
        screen = CartScreen(self.driver, self.timeout)
        screen.open_cart()
        screen.wait_until_loaded()
        return screen

    # --- catalogue -------------------------------------------------------------------
    def open_product(self, name: str) -> Product:
        log.info("open product %r", name)
        self.catalogue.by_name(name)  # fail fast with the list of real names on a typo
        self._to_catalog().open_product(name)
        self._open_product = name
        return ProductScreen(self.driver, self.timeout).read()

    def catalogue_price(self, name: str) -> Money:
        return self.catalogue.by_name(name).price

    def catalogue_data(self) -> Catalogue:
        return self.catalogue

    def find_sold_out_product(self) -> str | None:
        sold_out = self.catalogue.sold_out()
        return sold_out[0].name if sold_out else None

    # --- cart ------------------------------------------------------------------------
    def add(self, name: str, quantity: int = 1) -> None:
        log.info("add %d x %r", quantity, name)
        self._on_product(name).add_to_cart(quantity)

    def try_add(self, name: str) -> bool:
        if not self.catalogue.by_name(name).available:
            return False
        self.add(name)
        return True

    def prefill(self, items: Mapping[str, int]) -> None:
        """No API in a native app: set up through the UI (slower; Day 9, 4.4)."""
        for name, quantity in items.items():
            self.add(name, quantity)

    def set_quantity(self, name: str, quantity: int) -> None:
        self._cart_screen().set_quantity(name, quantity)

    def remove(self, name: str) -> None:
        self._cart_screen().remove(name)

    def cart(self) -> Cart:
        screen = self._cart_screen()
        cart = screen.read()
        self._check_consistent(
            cart, screen.cart_count(), None if cart.item_count == 0 else screen.items_label()
        )
        return cart

    @staticmethod
    def _check_consistent(cart: Cart, badge: int, items_label: int | None) -> None:
        """Three views of the same cart on one screen must agree (no API to compare with)."""
        problems = []
        lines_total = sum((line.line_total for line in cart.lines), Money.zero(cart.total.currency))
        if cart.lines and lines_total != cart.total:
            problems.append(f"total {cart.total} vs sum of lines {lines_total}")
        if badge != cart.item_count:
            problems.append(f"header badge {badge} vs lines {cart.item_count}")
        if items_label is not None and items_label != cart.item_count:
            problems.append(f"'{items_label} items' label vs lines {cart.item_count}")
        if problems:
            raise CartInconsistencyError("cart screen disagrees with itself: " + "; ".join(problems))

    # --- not in this app ---------------------------------------------------------------
    def _unsupported(self, what: str) -> NotSupportedOnPlatformError:
        return NotSupportedOnPlatformError(f"My Demo App has no {what}")

    def catalogue_listing(self) -> list[ProductCard]:
        raise self._unsupported("catalogue-listing check implemented yet")

    def search(self, keyword: str) -> list[str]:
        raise self._unsupported(f"search (asked for {keyword!r})")

    def add_variant(self, name: str, variant: str, quantity: int = 1) -> None:
        raise self._unsupported(
            f"size/colour variants on one product (asked for {quantity} x {name!r} {variant!r}; "
            "colours are separate products)"
        )

    def go_to_checkout(self) -> str:
        raise self._unsupported("web checkout page (see tests/mobile for the app's checkout)")

    def checkout_summary(self) -> OrderSummary:
        raise self._unsupported("web order summary")

    def open_menu_page(self, link: str) -> str:
        raise self._unsupported(f"information pages (asked for {link!r})")

    def open_latest_article(self) -> tuple[str, str]:
        raise self._unsupported("blog")

    def open_missing_page(self) -> tuple[int | None, str]:
        raise self._unsupported("web addresses")
