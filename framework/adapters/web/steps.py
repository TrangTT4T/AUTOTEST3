"""``business_step``: name a part of a test, in the log and in the Playwright trace.

    with business_step(page, "Choose the variant M / Red"):
        product.select_variant(...)

In the Trace Viewer the actions appear grouped under that title, so a trace of an
end-to-end test reads like the workflow it checks. When tracing is off, grouping
is a no-op (checked with Playwright 1.63).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Page

log = logging.getLogger("shop.e2e")


@contextmanager
def business_step(page: Page, title: str) -> Iterator[None]:
    log.info("STEP %s", title)
    page.context.tracing.group(title)
    try:
        yield
    finally:
        page.context.tracing.group_end()
