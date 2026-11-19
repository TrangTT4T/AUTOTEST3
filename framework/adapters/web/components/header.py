"""Header: search box, account links, and the cart link. Present on every shop page."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from framework.adapters.web.guard import ensure_not_blocked


class Header:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(self._root)
        self.search_box = self.root.locator(self._search_box)
        self.log_in_link = self.root.locator(self._log_in_link)
        self.sign_up_link = self.root.locator(self._sign_up_link)
        self.cart_link = self.root.locator(self._cart_link)
        self.check_out_link = self.root.locator(self._check_out_link)

    def search(self, keyword: str) -> None:
        self.search_box.fill(keyword)
        self.search_box.press("Enter")
        self.page.wait_for_url("**/search?**")
        ensure_not_blocked(self.page)

    def cart_count(self) -> int:
        """The number shown right now. After an AJAX change use ``expect_cart_count``."""
        match = re.search(r"\d+", self.cart_link.inner_text())
        if match is None:
            raise AssertionError(f"cart link shows no number: {self.cart_link.inner_text()!r}")
        return int(match.group())

    def expect_cart_count(self, count: int) -> None:
        """Wait until the header shows ``count``.

        After Add to Cart the server answers first and the header text is
        updated a moment later, so a one-off read can still see the old number.
        """
        expect(self.cart_link).to_have_text(f"My Cart ({count})")

    def go_to_log_in(self) -> None:
        self.log_in_link.click()
        self.page.wait_for_url("**/account/login")

    def go_to_sign_up(self) -> None:
        self.sign_up_link.click()
        self.page.wait_for_url("**/account/register")

    # --- Locators -------------------------------------------------------------
    _root = "role=banner"
    # Inside the banner:
    _search_box = "role=textbox[name='Search']"
    _log_in_link = "role=link[name='Log In']"
    _sign_up_link = "role=link[name='Sign up']"
    _cart_link = r"role=link[name=/^My Cart \(\d+\)$/]"
    _check_out_link = "role=link[name='Check Out']"
