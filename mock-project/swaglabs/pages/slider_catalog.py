"""Dynamic catalogue with an auto-advancing slider: /dynamic-catalog-slider.html.

The slider keeps changing, so it is checked on a HISTORY of what was shown (recorded in the page),
not on one snapshot that may be taken mid-change.
"""

from __future__ import annotations

import re

from playwright.sync_api import expect

from swaglabs.pages.base import BasePage


class SliderCatalogPage(BasePage):
    PATH = "/dynamic-catalog-slider.html"

    def wait_until_loaded(self) -> None:
        expect(self.find(self._shown_name)).to_be_visible()

    def snapshot(self) -> tuple[str, str]:
        """(name on show, product the active dot names) - read together, in one call."""
        values = self.page.evaluate(
            "(s) => [document.querySelector(s.name).innerText,"
            " document.querySelector(s.active).getAttribute('aria-label')]",
            {"name": self._shown_name, "active": self._active_dot},
        )
        return str(values[0]), re.sub(r"^Show ", "", str(values[1]))

    def start_recording(self) -> None:
        self.page.evaluate(self._record_shown_js, {"name": self._shown_name, "container": self._container})

    def history(self) -> list[str]:
        return [str(n) for n in self.page.evaluate("() => window.__sliderHistory || []")]

    def pause(self, milliseconds: int) -> None:
        """Sampling cadence for watching the slider over time - NOT a wait for a state."""
        self.page.wait_for_timeout(milliseconds)

    def choose(self, product_name: str) -> None:
        self.find(self._dot.format(name=product_name)).click()

    # --- Locators -------------------------------------------------------------
    _container = "[data-test='dynamic-catalog-slider-container']"
    _shown_name = "[data-test='dynamic-catalog-slider-item-name']"
    _active_dot = "[data-test^='dynamic-catalog-slider-dot-'][aria-current='true']"
    _dot = "role=button[name='Show {name}']"

    # --- Scripts (run in the page) --------------------------------------------
    # Content that keeps changing is checked on a HISTORY recorded in the page by a
    # MutationObserver, not on a single racy snapshot.
    _record_shown_js = """(s) => {
        const shown = () => { const el = document.querySelector(s.name); return el ? el.innerText : null; };
        const history = window.__sliderHistory = [shown()];
        new MutationObserver(() => {
            const name = shown();
            if (name !== history[history.length - 1]) history.push(name);
        }).observe(document.querySelector(s.container),
                   {subtree: true, childList: true, characterData: true});
    }"""
