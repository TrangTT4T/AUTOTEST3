"""Article page: /blogs/news/<handle>."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage


class ArticlePage(BasePage):
    PATH_PREFIX = "/blogs/news"  # same blog as BlogPage.PATH (no import: blog.py imports this module)

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.article = self.find(self._article)
        self.heading = self.find(self._heading)

    def open_article(self, handle: str) -> ArticlePage:
        return self.open_path(f"{self.PATH_PREFIX}/{handle}")

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def heading_text(self) -> str:
        return self.heading.inner_text().strip()

    def author(self) -> str:
        """'Posted by Shopify' -> 'Shopify'."""
        for line in self.article.inner_text().splitlines():
            if line.strip().startswith("Posted by"):
                return line.strip().removeprefix("Posted by").strip()
        return ""

    # --- Locators -------------------------------------------------------------
    _article = "role=article"
    _heading = "role=article >> role=heading[level=2]"
