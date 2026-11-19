"""``Shop``: one entry point to every page object, for BDD adapters and plain Playwright tests.

    def test_catalogue_lists_seven_products(shop: Shop) -> None:
        assert len(shop.catalog().open().products()) == 7

Each method returns a fresh page object bound to the same browser page;
nothing is opened until you call its ``open...`` method.
"""

from __future__ import annotations

from playwright.sync_api import Page

from framework.adapters.web.api import StoreApi
from framework.adapters.web.components import MiniCart
from framework.adapters.web.pages import (
    ArticlePage,
    BlogPage,
    CartPage,
    CatalogPage,
    CheckoutPage,
    ContentPage,
    HomePage,
    LoginPage,
    NotFoundPage,
    ProductPage,
    RegisterPage,
    SearchResultsPage,
)
from framework.domain import Catalogue


class Shop:
    def __init__(self, page: Page, catalogue: Catalogue) -> None:
        self.page = page
        self.catalogue = catalogue
        self.api = StoreApi(page, catalogue)  # fast setup: shop.api.add_lines(...)

    def home(self) -> HomePage:
        return HomePage(self.page)

    def catalog(self) -> CatalogPage:
        return CatalogPage(self.page)

    def product(self) -> ProductPage:
        return ProductPage(self.page)

    def open_product(self, name: str) -> ProductPage:
        return ProductPage(self.page).open_for(self.catalogue.by_name(name))

    def cart(self) -> CartPage:
        return CartPage(self.page, self.catalogue)

    def mini_cart(self) -> MiniCart:
        return MiniCart(self.page, self.catalogue)

    def search(self) -> SearchResultsPage:
        return SearchResultsPage(self.page)

    def checkout(self) -> CheckoutPage:
        return CheckoutPage(self.page)

    def content(self) -> ContentPage:
        return ContentPage(self.page)

    def blog(self) -> BlogPage:
        return BlogPage(self.page)

    def article(self) -> ArticlePage:
        return ArticlePage(self.page)

    def login(self) -> LoginPage:
        return LoginPage(self.page)

    def register(self) -> RegisterPage:
        return RegisterPage(self.page)

    def not_found(self) -> NotFoundPage:
        return NotFoundPage(self.page)
