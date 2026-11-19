"""Product grid: the tiles on the home page, the catalogue, and search results."""

from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.adapters.web.selectors import quoted
from framework.domain import Money, ProductCard


class ProductGrid:
    def __init__(self, page: Page, scope: Locator | None = None) -> None:
        self.page = page
        root = scope if scope is not None else page.locator(self._root)
        self.cards = root.locator(self._card).filter(has=page.locator(self._card_name))

    def read(self) -> list[ProductCard]:
        result = []
        for card in self.cards.all():
            href = (card.get_attribute("href") or "").split("?")[0].rstrip("/")
            result.append(
                ProductCard(
                    name=card.locator(self._card_name).inner_text().strip(),
                    price=Money.parse(card.locator(self._card_price).inner_text()),
                    sold_out="sold out" in card.inner_text().lower(),
                    handle=href.split("/")[-1],
                )
            )
        return result

    def names(self) -> list[str]:
        return [card.name for card in self.read()]

    def open(self, name: str) -> None:
        self.cards.filter(
            has=self.page.locator(self._card_name_exact.format(name=quoted(name)))
        ).first.click()
        self.page.wait_for_url("**/products/**")

    # --- Locators -------------------------------------------------------------
    _root = "body"
    # A tile is a link to a product that contains a level-3 heading (the name).
    _card = "a[href*='/products/']"
    _card_name = "role=heading[level=3]"
    _card_name_exact = "role=heading[level=3][name={name} s]"
    _card_price = "role=heading[level=4]"
