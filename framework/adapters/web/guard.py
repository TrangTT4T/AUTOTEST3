"""Detects pages that are not the shop: bot checks, rate limits, outages."""

import re

from playwright.sync_api import Page

from framework.errors import EnvironmentBlockedError

BLOCKED_STATUSES = frozenset({403, 429, 503})
BOT_CHECK = re.compile(r"connection needs to be verified|verify you are human|just a moment", re.I)


def ensure_not_blocked(page: Page, status: int | None = None) -> None:
    """Raise EnvironmentBlockedError if the current page is a bot check, not the shop."""
    text = page.title() + " " + page.locator(_page_body).inner_text()[:500]
    if (status in BLOCKED_STATUSES) or BOT_CHECK.search(text):
        raise EnvironmentBlockedError(
            f"bot protection at {page.url} (HTTP {status}). "
            "Not a product defect: reduce load and rerun later."
        )


# --- Locators -------------------------------------------------------------------
_page_body = "body"  # the whole page: a bot check replaces the shop's content
