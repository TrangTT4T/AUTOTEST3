"""P2 · Finding products, sold-out protection, and shopper isolation."""

from collections.abc import Callable

import pytest

from framework.adapters.web.network import silence_third_parties
from framework.adapters.web.shop import Shop
from framework.adapters.web.steps import business_step
from framework.requirements_marks import covers

pytestmark = [pytest.mark.e2e, pytest.mark.p2]


@covers("REQ-01", "REQ-02")
def test_visitor_finds_a_product_by_search_and_sees_catalogue_details(shop: Shop) -> None:
    with business_step(shop.page, "Search for jackets"):
        shop.home().open().header.search("jacket")
        results = shop.search().results()
        assert {"Grey jacket", "Noir jacket"} <= {card.name for card in results}
        for card in results:  # every result card shows the catalogue price
            assert card.price == shop.catalogue.by_name(card.name).price, card

    with business_step(shop.page, "Open Grey jacket from the results"):
        shop.search().open_result("Grey jacket")
        product = shop.product()
        product.wait_until_loaded()
        shown = product.read()
        assert (shown.name, shown.price, shown.available) == ("Grey jacket", results[0].price, True)


@covers("REQ-06")
def test_sold_out_product_cannot_be_bought(shop: Shop) -> None:
    sold_out = shop.catalogue.sold_out()
    if not sold_out:
        pytest.skip("no sold-out product in the shop right now")
    name = sold_out[0].name

    with business_step(shop.page, f"Open the sold-out product {name!r}"):
        product = shop.open_product(name)
        assert product.is_sold_out()

    with business_step(shop.page, "Check that nothing reached the cart"):
        assert shop.api.cart().item_count == 0


@covers("REQ-04")
def test_two_shoppers_have_separate_carts(new_shop: Callable[..., Shop]) -> None:
    alice, bob = new_shop(), new_shop()
    for shopper in (alice, bob):
        silence_third_parties(shopper.page.context)

    with business_step(alice.page, "Alice adds a Grey jacket"):
        product = alice.open_product("Grey jacket")
        product.add_to_cart()
        product.header.expect_cart_count(1)

    with business_step(bob.page, "Bob's cart is still empty"):
        assert bob.cart().open().is_empty()
        assert bob.api.cart().item_count == 0
