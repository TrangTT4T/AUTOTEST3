"""Store adapter for the real shop, driven by Playwright.

``WebStore`` only orchestrates: page objects (through ``Shop``) own selectors
and waits, ``StoreApi`` owns JSON calls. It also keeps two cross-layer guarantees:

* setup goes through the fastest reliable layer (API), checks through the
  layer the requirement is about (UI);
* every cart read is checked against the shop's own cart data, so a page
  that renders the wrong numbers fails with ``CartInconsistencyError``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from playwright.sync_api import Page

from framework.adapters.web.diagnostics import BrowserDiagnostics
from framework.adapters.web.pages import CartPage, CheckoutPage, ProductPage
from framework.adapters.web.shop import Shop
from framework.domain import Cart, Catalogue, Money, OrderSummary, Product, ProductCard
from framework.errors import CartInconsistencyError

log = logging.getLogger("shop.web")

MISSING_PATH = "/pages/this-page-does-not-exist"


class WebStore:
    def __init__(self, page: Page, catalogue: Catalogue, diagnostics: BrowserDiagnostics) -> None:
        self.page = page
        self.catalogue = catalogue
        self.diagnostics = diagnostics
        self.shop = Shop(page, catalogue)
        self.api = self.shop.api
        self._product_page: ProductPage | None = None
        self._open_product: str | None = None
        self._checkout: CheckoutPage | None = None
        self._cart: Cart | None = None  # cached snapshot; None = must re-read

    # --- catalogue -------------------------------------------------------
    def open_product(self, name: str) -> Product:
        log.info("open product %r", name)
        self._leave_page()
        self._product_page = self.shop.open_product(name)
        self._open_product = name
        return self._product_page.read()

    def _on_product_page(self, name: str) -> ProductPage:
        if self._open_product != name or self._product_page is None:
            self.open_product(name)
        if self._product_page is None:
            raise RuntimeError(f"open_product({name!r}) did not leave a product page open")
        return self._product_page

    def catalogue_price(self, name: str) -> Money:
        return self.catalogue.by_name(name).price

    def catalogue_data(self) -> Catalogue:
        return self.catalogue

    def catalogue_listing(self) -> list[ProductCard]:
        log.info("read the catalogue page")
        self._leave_page()
        return self.shop.catalog().open().products()

    def find_sold_out_product(self) -> str | None:
        sold_out = self.catalogue.sold_out()
        return sold_out[0].name if sold_out else None

    def search(self, keyword: str) -> list[str]:
        log.info("search %r", keyword)
        self._leave_page()
        self.shop.home().open().header.search(keyword)
        return self.shop.search().titles()

    # --- cart ------------------------------------------------------------
    def add(self, name: str, quantity: int = 1) -> None:
        log.info("add %d x %r through the UI", quantity, name)
        self._on_product_page(name).add_to_cart(quantity)
        self._cart = None

    def add_variant(self, name: str, variant: str, quantity: int = 1) -> None:
        log.info("add %d x %r (%s) through the UI", quantity, name, variant)
        page = self._on_product_page(name)
        page.select_variant(self.catalogue.by_name(name).variant(variant))
        page.add_to_cart(quantity)
        self._cart = None

    def try_add(self, name: str) -> bool:
        page = self._on_product_page(name)
        if page.is_sold_out():
            log.info("%r is sold out; Add to Cart is disabled", name)
            return False
        self.add(name)
        return True

    def prefill(self, items: Mapping[str, int]) -> None:
        log.info("prefill cart through the API: %s", dict(items))
        lines = [(self.catalogue.by_name(n).first_available_variant(), q) for n, q in items.items()]
        self.api.add_lines(lines)
        self._cart = None

    def set_quantity(self, name: str, quantity: int) -> None:
        log.info("set quantity of %r to %d", name, quantity)
        self._open_cart_page().set_quantity(name, quantity)
        self._cart = None

    def remove(self, name: str) -> None:
        log.info("remove %r", name)
        self._open_cart_page().remove_all(name)
        self._cart = None

    def cart(self) -> Cart:
        if self._cart is None:
            page = self._open_cart_page()
            ui_cart = page.read()
            data_cart = self.api.cart()
            self._check_consistent(ui_cart, data_cart, page.header_count())
            self._cart = ui_cart
        return self._cart

    # --- navigation ------------------------------------------------------
    def go_to_checkout(self) -> str:
        log.info("proceed to checkout (stops before any data entry)")
        self._open_cart_page().check_out()
        self._leave_page()
        self._checkout = self.shop.checkout()
        self._checkout.wait_until_loaded()
        return self._checkout.page_title()

    def checkout_summary(self) -> OrderSummary:
        if self._checkout is None:
            self.go_to_checkout()
        if self._checkout is None:
            raise RuntimeError("go_to_checkout() did not reach the checkout page")
        return self._checkout.order_summary()

    def open_menu_page(self, link: str) -> str:
        log.info("open menu page %r", link)
        self._leave_page()
        self.shop.home().open().menu.open(link)
        return self.page.title()

    def open_latest_article(self) -> tuple[str, str]:
        self._leave_page()
        blog = self.shop.blog().open()
        listed = blog.article_list()[0].title
        log.info("open latest article %r", listed)
        return listed, blog.open_article(listed).heading_text()

    def open_missing_page(self) -> tuple[int | None, str]:
        self._leave_page()
        page = self.shop.not_found().open_missing(MISSING_PATH)
        return page.last_status, page.page_title()

    # --- internals -------------------------------------------------------
    def _open_cart_page(self) -> CartPage:
        self._leave_page()
        return self.shop.cart().open()

    def _leave_page(self) -> None:
        self._product_page = None
        self._open_product = None
        self._checkout = None

    @staticmethod
    def _check_consistent(ui: Cart, data: Cart, header_count: int) -> None:
        problems = []
        if ui.quantities() != data.quantities():
            problems.append(f"quantities: page {ui.quantities()} vs data {data.quantities()}")
        if ui.total != data.total:
            problems.append(f"total: page {ui.total} vs data {data.total}")
        if header_count != data.item_count:
            problems.append(f"header 'My Cart ({header_count})' vs data item_count {data.item_count}")
        if problems:
            raise CartInconsistencyError("cart page disagrees with cart data: " + "; ".join(problems))
