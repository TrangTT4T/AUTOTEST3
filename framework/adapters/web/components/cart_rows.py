"""Cart rows, shared by the cart page and the mini-cart, which use the same row markup."""

from __future__ import annotations

from playwright.sync_api import Locator

from framework.domain import CartLine, Catalogue, Money
from framework.errors import AmbiguousTargetError


def the_only_row(rows: Locator, name: str) -> Locator:
    """The single cart row of ``name``; several rows (variants) or none make the request ambiguous.

    Replaces ``.first``, which silently picked one variant and left the others unchanged.
    The rows are rendered with the page, so counting them once is not a race.
    """
    count = rows.count()
    if count != 1:
        raise AmbiguousTargetError(
            f"{name!r} has {count} lines in the cart; this action needs exactly one "
            "(with several variants, address one variant)"
        )
    return rows


def read_rows(rows: Locator, catalogue: Catalogue) -> list[CartLine]:
    lines = []
    for row in rows.all():
        link = row.locator(ROW_TITLE_LINK)
        handle = (link.get_attribute("href") or "").rstrip("/").split("/")[-1]
        heading = " ".join(link.inner_text().split())  # "Noir jacket - M / Blue"
        lines.append(
            CartLine(
                name=catalogue.by_handle(handle).name,
                variant=heading.split(" - ", 1)[-1],
                quantity=int(row.locator(ROW_QUANTITY).input_value()),
                line_total=Money.parse(row.locator(ROW_TOTAL).inner_text()),
            )
        )
    return lines


# --- Locators (inside one cart row) ---------------------------------------------
ROW_TITLE_LINK = "role=heading[level=3] >> role=link"
ROW_QUANTITY = "input[name='updates[]']"
ROW_TOTAL = ".total"
