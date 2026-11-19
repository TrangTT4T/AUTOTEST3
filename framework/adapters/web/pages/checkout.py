"""Checkout page (read-only). The framework never enters contact or payment data.

The order summary is read from two accessible tables Shopify renders:
"Shopping cart" (lines) and "Cost summary" (subtotal, total, included tax).
The included-tax line is not always shown (observed both "Including £18.33 in
taxes" and an empty "Taxes" row on 2026-11-18); ``included_tax`` is then None.
On narrow (mobile) viewports Shopify collapses the summary behind a toggle;
this page object expects a desktop viewport, pytest-playwright's default.
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from framework.adapters.web.guard import ensure_not_blocked
from framework.adapters.web.pages.base import BasePage
from framework.domain import CartLine, Money, OrderSummary


class CheckoutPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.contact_section = self.find(self._contact_section)
        self.summary = self.find(self._summary)
        self.lines_table = self.find(self._lines_table)
        self.costs_table = self.find(self._costs_table)

    def wait_until_loaded(self) -> None:
        self.page.wait_for_url("**/checkouts/**")
        ensure_not_blocked(self.page)
        expect(self.contact_section).to_be_visible()

    def _cost(self, row_name_prefix: str) -> Locator:
        return self.costs_table.locator(self._row).filter(
            has=self.find(self._row_header_starting.format(prefix=re.escape(row_name_prefix)))
        )

    def order_summary(self) -> OrderSummary:
        self.wait_until_loaded()
        expect(self.lines_table).to_be_visible()
        lines = []
        # Data rows have 4 cells: image (with quantity badge), description, quantity, price.
        for row in self.lines_table.locator(self._row).filter(has=self.find(self._cell)).all():
            cells = row.locator(self._cell)
            description = cells.nth(1).locator(self._paragraph).all_inner_texts()
            lines.append(
                CartLine(
                    name=description[0].strip(),
                    variant=description[1].strip() if len(description) > 1 else "",
                    quantity=int(cells.nth(2).inner_text()),
                    line_total=Money.parse(cells.nth(3).inner_text()),
                )
            )
        tax_row = self.costs_table.locator(self._row_header).filter(has_text="in taxes")
        return OrderSummary(
            lines=tuple(lines),
            subtotal=Money.parse(self._cost("Subtotal").locator(self._cell).first.inner_text()),
            total=Money.parse(self._cost("Total").locator(self._cell).first.inner_text()),
            included_tax=Money.parse(tax_row.inner_text()) if tax_row.count() else None,
        )

    # --- Locators -------------------------------------------------------------
    _contact_section = "role=heading[name='Contact']"
    _summary = "role=complementary"
    _lines_table = "role=complementary >> role=table[name='Shopping cart']"
    _costs_table = "role=complementary >> role=table[name='Cost summary']"
    # Inside the tables:
    _row = "role=row"
    _cell = "role=cell"
    _row_header = "role=rowheader"
    # A row header starts with its label ("Subtotal …"); anchored: "Total" never matches "Subtotal".
    _row_header_starting = "role=rowheader[name=/^{prefix}/]"
    _paragraph = "p"
