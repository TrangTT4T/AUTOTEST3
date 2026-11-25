"""Login page (/account/login), with the password-recovery form on the same page.

A MANUAL flow in the BDD suite (REQ-08): the page loads CAPTCHA scripts, and on 2026-11-18 a
wrong-password attempt returned to the login page without any visible message (likely
intercepted). The page object is complete so that a test environment without CAPTCHA can use it.
Password recovery sends real e-mail, so it is not exercised against the public demo store.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage


class LoginPage(BasePage):
    PATH = "/account/login"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = self.find(self._heading)
        self.email = self.find(self._email)
        self.password = self.find(self._password)
        self.sign_in_button = self.find(self._sign_in_button)
        self.forgot_password_link = self.find(self._forgot_password_link)
        self.form_errors = self.find(self._form_errors)
        self.recovery_heading = self.find(self._recovery_heading)
        self.recovery_email = self.find(self._recovery_email)
        self.recovery_submit = self.find(self._recovery_submit)
        self.recovery_cancel = self.find(self._recovery_cancel)

    def open(self) -> LoginPage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def fill_credentials(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)

    def sign_in(self, email: str, password: str) -> None:
        self.fill_credentials(email, password)
        # Wait for the server's answer to THIS submit. A load-state wait would return at once:
        # the current page is already loaded, so it proves nothing about the sign-in.
        with self.page.expect_response(lambda r: r.request.method == "POST" and "/account/login" in r.url):
            self.sign_in_button.click()

    def errors(self) -> list[str]:
        return [e.strip() for e in self.form_errors.all_inner_texts() if e.strip()]

    def show_password_recovery(self) -> None:
        self.forgot_password_link.click()
        expect(self.recovery_heading).to_be_visible()
        expect(self.email).to_be_hidden()

    def hide_password_recovery(self) -> None:
        self.recovery_cancel.click()
        expect(self.heading).to_be_visible()

    def request_password_reset(self, email: str) -> None:
        """Sends a real e-mail on a real shop: use only in an owned test environment."""
        self.show_password_recovery()
        self.recovery_email.fill(email)
        self.recovery_submit.click()

    # --- Locators -------------------------------------------------------------
    _heading = "role=heading[name='Customer Login']"
    _email = "role=textbox[name='Email Address']"
    _password = "role=textbox[name='Password']"
    _sign_in_button = "role=button[name='Sign In']"
    _forgot_password_link = "role=link[name='Forgot your password?']"
    _form_errors = "form .errors"
    # Password recovery is a second form on the same page, shown by the link above.
    _recovery_heading = "role=heading[name='Reset Password']"
    _recovery_email = "#recover-email"  # no accessible label
    _recovery_submit = "role=button[name='Submit']"
    _recovery_cancel = "role=link[name='Cancel']"
