"""Network control helpers: isolate tests from third parties, simulate failures.

Observed on the shop (2026-11-18): each page sends dozens of telemetry requests.
Aborting them made the scripts RETRY (74 requests instead of 65); answering with
an empty 204 ended the retries. Silenced requests are counted, so a report can
show what the test did not depend on.
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Page, Route

THIRD_PARTY = re.compile(
    r"monorail|/api/collect|/v1/metrics|/\.well-known/shopify/fec"
    r"|facebook\.(net|com)|adroll\.com|shopifysvc\.com|extensions\.shopifycdn\.com|sauceapp\.io"
)


def silence_third_parties(target: BrowserContext | Page) -> Counter[str]:
    """Answer telemetry and third-party scripts with an empty 204. Returns a live count per host."""
    silenced: Counter[str] = Counter()

    def answer(route: Route) -> None:
        silenced[urlsplit(route.request.url).netloc] += 1
        route.fulfill(status=204, body="")

    target.route(THIRD_PARTY, answer)
    return silenced


def simulate_failure(target: BrowserContext | Page, url: str, status: int | None = 500) -> None:
    """Make matching requests fail: with an HTTP ``status``, or (``status=None``) like a broken network."""

    def fail(route: Route) -> None:
        if status is None:
            route.abort()
        else:
            route.fulfill(status=status, content_type="application/json", body=f'{{"status": {status}}}')

    target.route(url, fail)
