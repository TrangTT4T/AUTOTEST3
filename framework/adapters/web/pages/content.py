"""Content pages: /pages/<handle> (About Us, ...)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage


class ContentPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = self.find(self._heading).filter(has_not=self.find(self._logo))

    def open_page(self, handle: str) -> ContentPage:
        return self.open_path(f"/pages/{handle}")

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def heading_text(self) -> str:
        return self.heading.inner_text().strip()

    # --- Locators -------------------------------------------------------------
    # The logo is also an <h1> (it contains the "Sauce Demo" image); it is excluded.
    _heading = "role=heading[level=1]"
    _logo = "role=img[name='Sauce Demo']"
