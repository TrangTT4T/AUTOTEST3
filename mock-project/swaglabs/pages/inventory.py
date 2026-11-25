"""Products page (the catalogue): /inventory.html."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from swaglabs.domain import Card, Money, Product, SortOrder
from swaglabs.pages.base import BasePage
from swaglabs.pages.header import Header


class InventoryPage(BasePage):
    PATH = "/inventory.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = Header(page)
        self.list = self.find(self._list)
        self.card_names = self.find(self._card_name)
        self.sort_select = self.find(self._sort)

    def wait_until_loaded(self) -> None:
        expect(self.list).to_be_visible()

    # --- reading -------------------------------------------------------------
    def read_cards(self) -> list[Card]:
        selectors = {"name": self._card_name, "price": self._card_price, "image": self._card_image}
        rows = self.find(self._card).evaluate_all(self._read_cards_js, selectors)
        return [Card(r["name"], Money.parse(r["price"]), r["image"]) for r in rows]

    def expect_names(self, names: list[str]) -> None:
        """Retrying check of the whole list, in order."""
        expect(self.card_names).to_have_text(names)

    def expect_first_name(self, name: str) -> None:
        expect(self.card_names.first).to_have_text(name)

    def card(self, name: str) -> Locator:
        exact = re.compile(rf"^{re.escape(name)}$")
        return self.find(self._card).filter(has=self.page.locator(self._card_name, has_text=exact))

    def expect_offers_add(self, product: Product) -> None:
        expect(self.find(self._add.format(slug=product.slug))).to_be_visible()

    # --- acting --------------------------------------------------------------
    def sort_by(self, order: SortOrder) -> None:
        self.sort_select.select_option(order.value)

    def add(self, product: Product) -> None:
        self.find(self._add.format(slug=product.slug)).click()

    def tap_add(self, product: Product) -> None:
        self.find(self._add.format(slug=product.slug)).tap()

    def double_click_add(self, product: Product) -> None:
        self.find(self._add.format(slug=product.slug)).dblclick()

    def remove(self, product: Product) -> None:
        self.find(self._remove.format(slug=product.slug)).click()

    def expect_in_cart(self, product: Product) -> None:
        """The card's button turned into Remove: the add was accepted."""
        expect(self.find(self._remove.format(slug=product.slug))).to_be_visible()

    def open_product(self, name: str) -> None:
        """Click the product's name on ITS card - the way a shopper does."""
        self.card(name).locator(self._card_name).click()

    # --- Locators -------------------------------------------------------------
    _list = "[data-test='inventory-list']"
    _card = "[data-test='inventory-item']"
    _card_name = "[data-test='inventory-item-name']"
    _card_price = "[data-test='inventory-item-price']"
    _card_image = "img.inventory_item_img"
    _sort = "[data-test='product-sort-container']"
    _add = "[data-test='add-to-cart-{slug}']"
    _remove = "[data-test='remove-{slug}']"

    # --- Scripts (run in the page) --------------------------------------------
    # One round trip reads every card at once: a consistent snapshot, even if the page re-renders.
    _read_cards_js = """(cards, s) => cards.map(card => ({
        name: card.querySelector(s.name).innerText,
        price: card.querySelector(s.price).innerText,
        image: card.querySelector(s.image).getAttribute('src'),
    }))"""
