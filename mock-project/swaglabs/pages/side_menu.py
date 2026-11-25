"""The side menu (burger): logout, reset app state, about."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


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
