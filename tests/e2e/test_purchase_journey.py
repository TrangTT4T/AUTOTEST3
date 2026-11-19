"""P1 · The purchase journey: catalogue → variant → search → cart → checkout summary."""

import pytest
from playwright.sync_api import expect

from framework.adapters.web.shop import Shop
from framework.adapters.web.steps import business_step
from framework.requirements_marks import covers

pytestmark = [pytest.mark.e2e, pytest.mark.p1]


@covers("REQ-01", "REQ-02", "REQ-03", "REQ-04", "REQ-05", "REQ-07")
def test_customer_buys_two_products_up_to_checkout(shop: Shop) -> None:
    noir = shop.catalogue.by_name("Noir jacket")
    sandals = shop.catalogue.by_name("Bronze sandals")

    with business_step(shop.page, "Browse the catalogue and open Noir jacket"):
        shop.catalog().open().open_product("Noir jacket")
        product = shop.product()
        product.wait_until_loaded()
        expect(product.price).to_have_text(str(noir.price))

    with business_step(shop.page, "Choose M / Red and add it to the cart"):
        product.select_variant(noir.variant("M / Red"))
        product.add_to_cart()
        product.header.expect_cart_count(1)

    with business_step(shop.page, "Find sandals with the search box and add two"):
        product.header.search("sandals")
        shop.search().open_result("Bronze sandals")
        sandals_page = shop.product()
        sandals_page.wait_until_loaded()
        sandals_page.add_to_cart(2)
        sandals_page.header.expect_cart_count(3)

    with business_step(shop.page, "Review the cart"):
        cart = shop.cart().open().read()
        assert cart.quantities() == {"Noir jacket": 1, "Bronze sandals": 2}, cart.describe()
        assert ("Noir jacket", "M / Red") in {(line.name, line.variant) for line in cart.lines}
        assert cart.total == noir.price + sandals.price * 2, cart.describe()
        assert shop.api.cart().quantities() == cart.quantities(), "cart page and cart data disagree"

    with business_step(shop.page, "Reduce the sandals to one"):
        shop.cart().set_quantity("Bronze sandals", 1)
        cart_page = shop.cart().open()
        cart = cart_page.read()
        assert cart.total == noir.price + sandals.price, cart.describe()

    with business_step(shop.page, "Proceed to checkout and compare the order summary"):
        cart_page.check_out()
        summary = shop.checkout().order_summary()
        assert summary.quantities() == cart.quantities()
        assert summary.subtotal == cart.total
