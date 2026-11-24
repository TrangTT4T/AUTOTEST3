"""Blog list (/blogs/news) and article pages (/blogs/news/<handle>)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage
from framework.adapters.web.selectors import quoted
from framework.domain import ArticleSummary


class BlogPage(BasePage):
    PATH = "/blogs/news"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.articles = self.find(self._articles)

    def open(self) -> BlogPage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.articles.first).to_be_visible()

    def article_list(self) -> list[ArticleSummary]:
        result = []
        for article in self.articles.all():
            link = article.locator(self._article_title_link)
            result.append(
                ArticleSummary(
                    title=link.inner_text().strip(),
                    date=article.inner_text().strip().splitlines()[0].strip(),
                    handle=(link.get_attribute("href") or "").rstrip("/").split("/")[-1],
                )
            )
        return result

    def open_article(self, title: str) -> ArticlePage:
        # No .first: one link per title (checked live); strict mode reports a duplicate title.
        self.articles.locator(self._article_link_named.format(title=quoted(title))).click()
        self.page.wait_for_url("**/blogs/news/**")
        page = ArticlePage(self.page)
        page.wait_until_loaded()
        return page

    # --- Locators -------------------------------------------------------------
    _articles = "role=article"
    _article_title_link = "role=heading[level=2] >> role=link"  # inside one article
    _article_link_named = "role=link[name={title} s]"  # inside the articles


class ArticlePage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.article = self.find(self._article)
        self.heading = self.find(self._heading)

    def open_article(self, handle: str) -> ArticlePage:
        return self.open_path(f"{BlogPage.PATH}/{handle}")

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
