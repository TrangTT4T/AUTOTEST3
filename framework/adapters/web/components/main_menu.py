"""Main menu: Home, Catalog, Blog, About Us (plus two third-party widget links)."""

from __future__ import annotations

from playwright.sync_api import Page

from framework.adapters.web.guard import ensure_not_blocked
from framework.adapters.web.selectors import quoted


class MainMenu:
    # "Wish list" and "Refer a friend" open widgets of a third-party app ("Sauce"),
    # not shop pages, so they are not navigation targets for tests.
    PAGES = ("Home", "Catalog", "Blog", "About Us")

    def __init__(self, page: Page) -> None:
        self.page = page
        self.links = page.locator(self._links)

    def names(self) -> list[str]:
        return [t.strip() for t in self.links.all_inner_texts() if t.strip()]

    def open(self, name: str) -> None:
        link = self.page.locator(self._link_named.format(name=quoted(name)))
        target = link.get_attribute("href")
        link.click()
        self.page.wait_for_url(f"**{target}")
        ensure_not_blocked(self.page)

    # --- Locators -------------------------------------------------------------
    # The main menu is the only navigation built from list items;
    # the header and footer repeat some links outside a list.
    _links = "role=listitem >> role=link"
    _link_named = "role=listitem >> role=link[name={name} s]"
