"""Header and side menu: present on every page after login."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


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


class SideMenu:
    def __init__(self, page: Page) -> None:
        self.page = page

    def find(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def wait_until_open(self) -> None:
        expect(self.find(self._logout)).to_be_visible()

    def entries(self) -> list[str]:
        return [text.strip() for text in self.find(self._entries).all_inner_texts()]

    def log_out(self) -> None:
        self.find(self._logout).click()

    def reset_app_state(self) -> None:
        self.find(self._reset).click()

    def close(self) -> None:
        self.find(self._close).click()
        expect(self.find(self._logout)).to_be_hidden()

    # --- Locators -------------------------------------------------------------
    # Top-level entries only: the Dynamic Catalog sub-menu has its own links.
    _entries = ".bm-item-list > a[data-test$='-sidebar-link']"
    _logout = "[data-test='logout-sidebar-link']"
    _reset = "[data-test='reset-sidebar-link']"
    _close = "role=button[name='Close Menu']"
