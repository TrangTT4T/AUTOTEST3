import pytest

from framework.adapters.web.network import THIRD_PARTY
from framework.requirements_marks import covers

SHOP = "https://sauce-demo.myshopify.com"


@pytest.mark.parametrize(
    "url",
    [
        f"{SHOP}/.well-known/shopify/monorail/unstable/produce_batch",
        f"{SHOP}/api/collect",
        f"{SHOP}/.well-known/shopify/fec/produce",
        "https://connect.facebook.net/en_US/fbevents.js",
        "https://otlp-http-production.shopifysvc.com/v1/metrics",
        "https://s.adroll.com/j/roundtrip.js",
    ],
)
def test_third_party_traffic_is_recognised(url: str) -> None:
    assert THIRD_PARTY.search(url)


@pytest.mark.parametrize(
    "url",
    [
        f"{SHOP}/cart/add.js",
        f"{SHOP}/cart.js",
        f"{SHOP}/products/grey-jacket",
        f"{SHOP}/products.json",
        f"{SHOP}/checkouts/cn/abc/en-gb",
        f"{SHOP}/search?type=product&q=jacket",
    ],
)
def test_the_shops_own_requests_are_never_silenced(url: str) -> None:
    assert not THIRD_PARTY.search(url)


def test_covers_adds_one_marker_per_requirement() -> None:
    @covers("REQ-03", "REQ-04")
    def test_example() -> None: ...

    assert sorted(mark.name for mark in test_example.pytestmark) == ["REQ-03", "REQ-04"]  # type: ignore[attr-defined]
