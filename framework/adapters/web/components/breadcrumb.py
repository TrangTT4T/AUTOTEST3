"""Breadcrumb: "Home — Products", "Home — News", ... shown above most page titles.

Markup (observed 2026-11-18): ``<div id="breadcrumb">`` with a schema.org
"Home" item followed by plain links; the "—" separators are text nodes.
"""

from __future__ import annotations

from playwright.sync_api import Page


class Breadcrumb:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(self._root)
        self.links = self.root.locator(self._links)

    def trail(self) -> list[str]:
        return [" ".join(t.split()) for t in self.links.all_inner_texts() if t.strip()]

    def current(self) -> str:
        """The last item: the page you are on."""
        trail = self.trail()
        return trail[-1] if trail else ""

    # --- Locators -------------------------------------------------------------
    _root = "#breadcrumb"
    _links = "role=link"  # inside the breadcrumb
