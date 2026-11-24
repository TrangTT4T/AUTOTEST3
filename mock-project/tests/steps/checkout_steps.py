"""Steps for the checkout: customer details, the overview and the confirmation."""

from __future__ import annotations

from pytest_bdd import given, parsers, then, when

from swaglabs.app import SwagLabs
from swaglabs.domain import OrderSummary
from tests.steps.memo import Memo

DETAILS = parsers.re(
    r'I enter first name "(?P<first>[^"]*)", last name "(?P<last>[^"]*)" and postal code "(?P<postal>[^"]*)"'
)


@given("I am on the checkout information page")
def on_checkout_info(shop: SwagLabs) -> None:
    shop.cart().open().check_out()
    shop.checkout_info().wait_until_loaded()


@when(DETAILS)
def enter_details(shop: SwagLabs, first: str, last: str, postal: str) -> None:
    shop.checkout_info().enter_details(first, last, postal)


@when("I continue")
def continue_checkout(shop: SwagLabs) -> None:
    shop.checkout_info().continue_()


@then("I stay on the checkout information page")
def stay_on_info(shop: SwagLabs) -> None:
    shop.checkout_info().wait_until_loaded()


@then(parsers.parse('I see the checkout error "{message}"'))
def checkout_error(shop: SwagLabs, message: str) -> None:
    shop.checkout_info().expect_error(message)


@then("the overview lists the products in my cart at their reference prices")
def overview_lists_cart(shop: SwagLabs, memo: Memo) -> None:
    overview = shop.overview()
    overview.wait_until_loaded()
    assert overview.item_names() == [p.name for p in memo.cart_products]
    assert overview.item_prices() == [p.price for p in memo.cart_products]


@then("the overview shows the item total, tax and total for them")
def overview_totals(shop: SwagLabs, memo: Memo) -> None:
    shown = shop.overview().read_summary()
    assert not shown.problems(), shown.problems()
    expected = OrderSummary.expected_for((p.price for p in memo.cart_products), shop.catalogue.tax_rate)
    assert shown == expected


@when("I finish the order")
def finish_order(shop: SwagLabs) -> None:
    with shop.perf.measure("finish-order"):
        shop.overview().finish()
        shop.complete().wait_until_loaded()


@then(parsers.parse('I see the confirmation "{text}"'))
def see_confirmation(shop: SwagLabs, text: str) -> None:
    shop.complete().expect_heading(text)
