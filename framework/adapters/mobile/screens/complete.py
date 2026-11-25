"""Checkout confirmation: "Checkout Complete"."""

from __future__ import annotations

from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen


class CompleteScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._title)

    def title(self) -> str:
        return self.visible(self._title).text.strip()

    def continue_shopping(self) -> None:
        self.tap(self._continue)

    # --- Locators -----------------------------------------------------------------
    _title = by_id("completeTV", "fragment_checkout_complete")  # "Checkout Complete"
    _continue = by_accessibility_id("Tap to open catalog", "fragment_checkout_complete")
