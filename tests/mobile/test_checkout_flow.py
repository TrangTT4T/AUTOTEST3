"""P1 · The app's purchase journey up to "Checkout Complete" (a demo app: nothing is charged)."""

import pytest
from appium.webdriver.webdriver import WebDriver

from framework.adapters.mobile.forms import Address, Card
from framework.adapters.mobile.screens import (
    CartScreen,
    CatalogScreen,
    CompleteScreen,
    LoginScreen,
    PaymentScreen,
    ProductScreen,
    ReviewScreen,
    ShippingScreen,
)
from framework.adapters.mobile.steps import mobile_step
from framework.domain import Catalogue, Money
from framework.requirements_marks import covers

pytestmark = [pytest.mark.mobile, pytest.mark.p1]
DELIVERY = "5.99"  # fixed in the app: PlaceOrderFragment adds 5.99 to the cart total


@covers("REQ-03", "REQ-04", "REQ-07", "REQ-08")
def test_customer_completes_checkout_in_the_app(
    app: WebDriver, catalogue: Catalogue, shipping_address: Address, test_card: Card
) -> None:
    backpack = catalogue.by_name("Sauce Labs Backpack")

    with mobile_step("Open Sauce Labs Backpack and add two"):
        CatalogScreen(app).open_product(backpack.name)
        product = ProductScreen(app)
        assert product.read().price == backpack.price
        product.add_to_cart(2)

    with mobile_step("Review the cart"):
        cart_screen = CartScreen(app)
        cart_screen.open_cart()
        cart = cart_screen.read()
        assert cart.quantities() == {backpack.name: 2}, cart.describe()
        assert cart.total == backpack.price * 2, cart.describe()
        cart_screen.proceed_to_checkout()

    with mobile_step("Log in with the app's test account"):
        LoginScreen(app).log_in("bod@example.com", "10203040")

    with mobile_step("Enter the shipping address and the payment card"):
        ShippingScreen(app).submit(shipping_address)
        PaymentScreen(app).submit(test_card)

    with mobile_step("Review: items and total include delivery"):
        review = ReviewScreen(app)
        review.wait_until_loaded()
        assert review.item_count() == 2
        assert review.delivery() == Money.parse(DELIVERY, "USD")
        assert review.total() == backpack.price * 2 + review.delivery()
        review.place_order()

    with mobile_step("The order is confirmed"):
        complete = CompleteScreen(app)
        complete.wait_until_loaded()
        assert complete.title() == "Checkout Complete"
