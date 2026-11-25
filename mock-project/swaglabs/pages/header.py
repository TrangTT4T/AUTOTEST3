"""The header bar on every page after login: cart badge and the menu button."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from swaglabs.pages.side_menu import SideMenu


class Header:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.cart_link = self.find(self._cart_link)
        self.cart_badge = self.find(self._cart_badge)
        self.title = self.find(self._title)

    def find(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def expect_cart_count(self, count: int) -> None:
        """Retrying check: the badge shows ``count`` (no badge at all for an empty cart)."""
        if count == 0:
            expect(self.cart_badge, "an empty cart shows no badge").to_have_count(0)
        else:
            expect(self.cart_badge).to_have_text(str(count))

    def cart_count(self) -> int:
        """One immediate read - use after the page has settled (prefer ``expect_cart_count``)."""
        return int(self.cart_badge.inner_text()) if self.cart_badge.count() else 0

    def open_cart(self, *, touch: bool = False) -> None:
        if touch:
            self.cart_link.tap()
        else:
            self.cart_link.click()

    def open_menu(self, *, touch: bool = False) -> SideMenu:
        button = self.find(self._menu_button)
        if touch:
            button.tap()
        else:
            button.click()
        menu = SideMenu(self.page)
        menu.wait_until_open()
        return menu

    # --- Locators -------------------------------------------------------------
    _cart_link = "[data-test='shopping-cart-link']"
    _cart_badge = "[data-test='shopping-cart-badge']"
    _title = "[data-test='title']"
    _menu_button = "role=button[name='Open Menu']"
