"""Login screen: shown when checkout needs a signed-in user."""

from __future__ import annotations

from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen


class LoginScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._submit)

    def log_in(self, username: str, password: str) -> None:
        self.wait_until_loaded()
        self.type_into(self._username, username)
        self.type_into(self._password, password)
        self.tap(self._submit)

    def password_error(self) -> str:
        return self.visible(self._password_error).text.strip()

    def username_error(self) -> str:
        return self.visible(self._username_error).text.strip()

    # --- Locators -----------------------------------------------------------------
    _title = by_id("loginTV", "fragment_login")
    _username = by_id("nameET", "fragment_login")
    _password = by_id("passwordET", "fragment_login")
    _submit = by_accessibility_id("Tap to login with given credentials", "fragment_login")
    _username_error = by_id("nameErrorTV", "fragment_login")
    _password_error = by_id("passwordErrorTV", "fragment_login")  # also shows "locked out"
