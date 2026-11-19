"""Cart page, mini-cart, and checkout summary."""

from decimal import Decimal

import pytest

from framework.adapters.web.shop import Shop
from framework.domain import Money, Variant

pytestmark = pytest.mark.web


def _variant(shop: Shop, name: str) -> Variant:
    return shop.catalogue.by_name(name).first_available_variant()


def test_empty_cart_page_and_continue_shopping(shop: Shop) -> None:
    cart = shop.cart().open()
    assert cart.is_empty()
    assert cart.read().item_count == 0
    cart.continue_shopping()
    shop.catalog().wait_until_loaded()


def test_cart_page_reads_lines_and_total(shop: Shop) -> None:
    shop.page.goto("/cart")
    shop.api.add_lines([(_variant(shop, "Grey jacket"), 2), (_variant(shop, "Bronze sandals"), 1)])
    cart = shop.cart().open().read()
    assert cart.quantities() == {"Grey jacket": 2, "Bronze sandals": 1}
    assert cart.total == Money(Decimal("149.99"))


def test_mini_cart_shows_the_cart_after_a_page_load(shop: Shop) -> None:
    product = shop.open_product("Grey jacket")
    product.add_to_cart()
    product.header.expect_cart_count(1)
    shop.page.reload()
    assert shop.mini_cart().read().quantity_of("Grey jacket") == 1


def test_mini_cart_opens_and_removes_a_product(shop: Shop) -> None:
    product = shop.open_product("Grey jacket")
    product.add_to_cart()
    product.header.expect_cart_count(1)
    shop.page.reload()  # the drawer is only rendered on page load (see the xfail test below)
    mini_cart = shop.mini_cart()
    assert not mini_cart.is_open()
    mini_cart.open()
    assert mini_cart.is_open()
    mini_cart.remove("Grey jacket")
    assert shop.cart().open().is_empty()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,  # only a failed check is the known defect; anything else must surface
    reason="Known shop defect (2026-11-18): the mini-cart is not refreshed after an AJAX add. "
    "strict=True: if the shop fixes it, this test fails as XPASS and must be updated.",
)
def test_mini_cart_updates_without_a_page_load(shop: Shop) -> None:
    product = shop.open_product("Grey jacket")
    product.add_to_cart()
    product.header.expect_cart_count(1)
    assert shop.mini_cart().read().quantity_of("Grey jacket") == 1


def test_checkout_summary_matches_the_cart(shop: Shop) -> None:
    shop.page.goto("/cart")
    shop.api.add_lines([(_variant(shop, "Grey jacket"), 2)])
    shop.cart().open().check_out()
    summary = shop.checkout().order_summary()
    assert summary.quantities() == {"Grey jacket": 2}
    assert summary.subtotal == summary.total == Money(Decimal("110.00"))
    # Tax display is volatile: one run showed "Including £18.33 in taxes", a later one an
    # empty "Taxes" row. No requirement covers it, so check it only when it is shown:
    # then it must be the UK VAT (20 %) included in the total, i.e. total / 6.
    if summary.included_tax is not None:
        assert summary.included_tax == Money(summary.total.amount / 6)
