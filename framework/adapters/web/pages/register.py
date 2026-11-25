"""Registration page (/account/register).

A MANUAL flow in the BDD suite (REQ-08), like login: the page loads CAPTCHA scripts. Submitting
creates a real account, so it is never exercised against the public demo store.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from framework.adapters.web.pages.base import BasePage
from framework.domain import Customer


class RegisterPage(BasePage):
    PATH = "/account/register"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = self.find(self._heading)
        self.first_name = self.find(self._first_name)
        self.last_name = self.find(self._last_name)
        self.email = self.find(self._email)
        self.password = self.find(self._password)
        self.create_button = self.find(self._create_button)

    def open(self) -> RegisterPage:
        return self.open_path(self.PATH)

    def wait_until_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    def fill_form(self, customer: Customer) -> None:
        self.first_name.fill(customer.first_name)
        self.last_name.fill(customer.last_name)
        self.email.fill(customer.email)
        self.password.fill(customer.password)

    def register(self, customer: Customer) -> None:
        """Creates a real account on a real shop: use only in an owned test environment."""
        self.fill_form(customer)
        with self.page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/account")):
            self.create_button.click()

    # --- Locators -------------------------------------------------------------
    _heading = "role=heading[name='Create Account']"
    # Two testability defects: the labels are not linked to the inputs, and the
    # ids are duplicated (<div id="first_name"> wraps <input id="first_name">).
    # The form field names are unique and stable, so they are used.
    _first_name = "input[name='customer[first_name]']"
    _last_name = "input[name='customer[last_name]']"
    _email = "#create_customer input[name='customer[email]']"
    _password = "#create_customer input[name='customer[password]']"
    _create_button = "role=button[name='Create']"
