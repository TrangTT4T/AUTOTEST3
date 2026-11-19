"""Base page object: guarded navigation, a 'loaded' contract, and shared components."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page

from framework.adapters.web.components import Breadcrumb, Header, MainMenu
from framework.adapters.web.guard import ensure_not_blocked


class BasePage:
    """A page object owns the selectors and waits for one page.

    Selectors are declared as string constants in the ``Locators`` section at the
    bottom of each page class (see framework/adapters/web/selectors.py); methods
    use them through ``find``. ``open_path`` navigates and returns only once the
    page is really usable; every subclass defines what "loaded" means in
    ``wait_until_loaded``. Components present on every page are attributes.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.header = Header(page)
        self.menu = MainMenu(page)
        self.breadcrumb = Breadcrumb(page)
        self.last_status: int | None = None

    def find(self, selector: str) -> Locator:
        """A locator for one of this page's declared selectors."""
        return self.page.locator(selector)

    def open_path(self, path: str) -> Self:
        response = self.page.goto(path)
        self.last_status = response.status if response else None
        ensure_not_blocked(self.page, self.last_status)
        self.wait_until_loaded()
        return self

    def wait_until_loaded(self) -> None:
        """Override: wait for the element that proves this page is ready."""

    def page_title(self) -> str:
        """The browser tab title (``title`` is left free for page objects' own locators)."""
        return self.page.title()
