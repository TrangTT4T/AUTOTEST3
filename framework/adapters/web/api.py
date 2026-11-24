"""The shop's JSON endpoints, called from inside the browser page.

Calling ``fetch()`` in the page means requests carry the page's cookies:
a cart set up through the API is the same cart the UI shows.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from playwright.sync_api import Page

from framework.domain import Cart, CartLine, Catalogue, Money, Variant
from framework.errors import ApiRequestError, EnvironmentBlockedError

_FETCH = """async ([method, path, body]) => {
    const response = await fetch(path, {
        method,
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: body ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    try {
        return {status: response.status, json: JSON.parse(text)};
    } catch {
        return {status: response.status, json: null};
    }
}"""


class StoreApi:
    def __init__(self, page: Page, catalogue: Catalogue) -> None:
        self._page = page
        self._catalogue = catalogue

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        if not self._page.url.startswith("http"):
            self._page.goto("/robots.txt")  # any same-origin document gives fetch() the site's cookies
        result = self._page.evaluate(_FETCH, [method, path, body])
        # Judge the body, not the Content-Type header: this shop sends valid
        # JSON from /cart.js and /cart/add.js labelled "text/javascript".
        if result["json"] is None:
            raise EnvironmentBlockedError(f"{method} {path} returned HTTP {result['status']} without JSON")
        if result["status"] >= 400:
            # Not an AssertionError: a client never asserts. The step that USES the result decides
            # whether the product is wrong; a failed set-up call is reported as what it is.
            raise ApiRequestError(f"{method} {path} failed: HTTP {result['status']} {result['json']}")
        return result["json"]

    def add_lines(self, lines: Sequence[tuple[Variant, int]]) -> None:
        items = [{"id": variant.id, "quantity": quantity} for variant, quantity in lines]
        self._call("POST", "/cart/add.js", {"items": items})

    def cart(self) -> Cart:
        data = self._call("GET", "/cart.js")
        lines = tuple(
            CartLine(
                name=self._catalogue.by_handle(item["handle"]).name,
                variant=item["variant_title"] or "",
                quantity=int(item["quantity"]),
                line_total=Money.from_minor_units(int(item["line_price"]), data["currency"]),
            )
            for item in data["items"]
        )
        return Cart(lines, Money.from_minor_units(int(data["total_price"]), data["currency"]))
