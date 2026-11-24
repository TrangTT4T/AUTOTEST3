"""Login page: / (also where every protected page redirects to without a session)."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from swaglabs.pages.base import BasePage


class LoginPage(BasePage):
    PATH = "/"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username = self.find(self._username)
        self.password = self.find(self._password)
        self.login_button = self.find(self._login_button)
        self.error = self.find(self._error)

    def wait_until_loaded(self) -> None:
        expect(self.login_button).to_be_visible()

    def log_in(self, username: str, password: str) -> None:
        """Submit the form. Does NOT wait for the result: the caller decides what success means."""
        self.username.fill(username)
        self.password.fill(password)
        self.login_button.click()

    def expect_error(self, message: str) -> None:
        expect(self.error).to_have_text(message)

    def close_error(self) -> None:
        self.find(self._error_close).click()
        expect(self.error).to_have_count(0)

    def expect_fields_marked_invalid(self) -> None:
        for field in (self.username, self.password):
            expect(field).to_have_class(re.compile(self._invalid_class))

    # --- Locators -------------------------------------------------------------
    _username = "[data-test='username']"
    _password = "[data-test='password']"
    _login_button = "[data-test='login-button']"
    _error = "[data-test='error']"
    _error_close = "[data-test='error-button']"
    _invalid_class = r"(^|\s)error(\s|$)"  # a class token, not a selector
