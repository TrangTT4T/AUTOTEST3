"""Steps shared by several features: sessions, cart badge, stored cart, navigation."""

from __future__ import annotations

from pytest_bdd import given, parsers, then, when

from swaglabs.app import SwagLabs
from tests.steps.memo import Memo, quoted


@given("I am on the login page")
def on_login_page(shop: SwagLabs) -> None:
    shop.login_page().open()


@given("I am logged in")
def logged_in(shop: SwagLabs) -> None:
    shop.start_session()


@given(parsers.re(r"my cart holds (?P<names>\".+\")"))
def cart_holds(shop: SwagLabs, memo: Memo, names: str) -> None:
    memo.cart_products = [shop.catalogue.by_name(name) for name in quoted(names)]
    shop.seed_cart(memo.cart_products)
    shop.header.expect_cart_count(len(memo.cart_products))


@then(parsers.parse("the cart badge shows {count:d}"))
def badge_shows(shop: SwagLabs, count: int) -> None:
    shop.header.expect_cart_count(count)


@then("the cart badge is empty")
def badge_empty(shop: SwagLabs) -> None:
    shop.header.expect_cart_count(0)


@then("the stored cart is empty")
def stored_cart_empty(shop: SwagLabs) -> None:
    shop.eventually_stored_cart([])


@when("I reload the page")
def reload_page(shop: SwagLabs) -> None:
    shop.reload()


@when("I open the cart")
def open_cart(shop: SwagLabs) -> None:
    with shop.perf.measure("open-cart"):
        shop.header.open_cart()
        shop.cart().wait_until_loaded()


@when("I tap the cart")
def tap_cart(shop: SwagLabs) -> None:
    with shop.perf.measure("open-cart"):
        shop.header.open_cart(touch=True)
        shop.cart().wait_until_loaded()


@then(parsers.parse('the cart page lists only "{name}"'))
def cart_lists_only(shop: SwagLabs, name: str) -> None:
    shop.cart().expect_names([name])


@then("the page fits the screen without sideways scrolling")
def fits_screen(shop: SwagLabs) -> None:
    assert shop.fits_screen_width(), "the page is wider than the screen"
