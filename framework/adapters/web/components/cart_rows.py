"""Cart rows, shared by the cart page and the mini-cart, which use the same row markup."""

from __future__ import annotations

from playwright.sync_api import Locator

from framework.domain import CartLine, Catalogue, Money
from framework.errors import AmbiguousTargetError


class CartRows:
    """The product rows of one cart view (page or drawer); the caller scopes ``rows``."""

    def __init__(self, rows: Locator) -> None:
        self.rows = rows

    def read(self, catalogue: Catalogue) -> list[CartLine]:
        lines = []
        for row in self.rows.all():
            link = row.locator(self._title_link)
            handle = (link.get_attribute("href") or "").rstrip("/").split("/")[-1]
            heading = " ".join(link.inner_text().split())  # "Noir jacket - M / Blue"
            lines.append(
                CartLine(
                    name=catalogue.by_handle(handle).name,
                    variant=heading.split(" - ", 1)[-1],
                    quantity=int(row.locator(self._quantity).input_value()),
                    line_total=Money.parse(row.locator(self._total).inner_text()),
                )
            )
        return lines

    def the_only_one(self, name: str) -> Locator:
        """The single row of ``name``; several rows (variants) or none make the request ambiguous.

        Replaces ``.first``, which silently picked one variant and left the others unchanged.
        The rows are rendered with the page, so counting them once is not a race.
        """
        count = self.rows.count()
        if count != 1:
            raise AmbiguousTargetError(
                f"{name!r} has {count} lines in the cart; this action needs exactly one "
                "(with several variants, address one variant)"
            )
        return self.rows

    # --- Locators (inside one cart row) -----------------------------------------
    _title_link = "role=heading[level=3] >> role=link"
    _quantity = "input[name='updates[]']"
    _total = ".total"
