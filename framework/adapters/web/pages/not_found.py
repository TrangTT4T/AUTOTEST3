"""The shop's 404 page."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage


class NotFoundPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.code = self.find(self._code)
        self.homepage_link = self.find(self._homepage_link)

    def open_missing(self, path: str) -> NotFoundPage:
        return self.open_path(path)

    def wait_until_loaded(self) -> None:
        expect(self.code).to_be_visible()

    def is_shown(self) -> bool:
        return self.last_status == 404 and self.code.is_visible()

    # --- Locators -------------------------------------------------------------
    _code = "role=heading[level=2][name='404']"
    _homepage_link = "role=link[name='homepage']"
