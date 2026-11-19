"""Network control: what the browser sends, and how the shop handles failures.

Observed on 2026-11-18 (Day 7 reconnaissance): when /cart/add.js fails, the shop shows
no message; after an HTTP 500 the button turns into a disabled "Sold Out", and after a
network failure it stays disabled. The cart itself is not changed. The safety property
passes; the expected customer experience is recorded as strict xfail (a tripwire).
"""

from collections import Counter
from urllib.parse import parse_qs

import pytest
from playwright.sync_api import expect

from framework.adapters.web.network import simulate_failure
from framework.adapters.web.shop import Shop
from framework.adapters.web.steps import business_step
from framework.requirements_marks import covers

pytestmark = pytest.mark.e2e

ADD_TO_CART = "**/cart/add.js"


@pytest.mark.p1
@covers("REQ-03")
def test_selected_variant_is_what_the_server_receives(shop: Shop) -> None:
    variant = shop.catalogue.by_name("Noir jacket").variant("L / Red")
    product = shop.open_product("Noir jacket")
    product.select_variant(variant)

    with shop.page.expect_request(ADD_TO_CART) as request:  # observe only: nothing is mocked
        product.add_to_cart()

    assert parse_qs(request.value.post_data or "")["id"] == [str(variant.id)]


@pytest.mark.p2
@covers("REQ-03", "REQ-04")
@pytest.mark.parametrize("status", [500, 503])
def test_failed_add_to_cart_leaves_the_cart_unchanged(shop: Shop, status: int) -> None:
    product = shop.open_product("Grey jacket")

    with business_step(shop.page, f"The server answers Add to Cart with HTTP {status}"):
        simulate_failure(shop.page, ADD_TO_CART, status=status)
        assert product.click_add_to_cart().status == status

    with business_step(shop.page, "Nothing was added"):
        product.header.expect_cart_count(0)
        assert shop.api.cart().item_count == 0


@pytest.mark.p2
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,  # only a failed check is the known defect; anything else must surface
    reason="Shop defect (2026-11-18): after a failed Add to Cart the button stays disabled "
    "(after HTTP 500 it even reads 'Sold Out') and no message is shown, so the customer cannot retry.",
)
@pytest.mark.parametrize("failure", ["http-500", "network"], ids=["http-500", "network"])
def test_customer_can_retry_after_a_failed_add_to_cart(shop: Shop, failure: str) -> None:
    product = shop.open_product("Grey jacket")
    simulate_failure(shop.page, ADD_TO_CART, status=500 if failure == "http-500" else None)

    product.add_button.click()

    expect(product.add_button, "the customer must be able to try again").to_be_enabled(timeout=5000)


@pytest.mark.p2
def test_shop_works_with_third_party_scripts_silenced(shop: Shop, silenced: Counter[str]) -> None:
    product = shop.open_product("Grey jacket")
    product.add_to_cart()
    product.header.expect_cart_count(1)
    assert sum(silenced.values()) > 0, "expected the shop to load third-party telemetry"
