"""P2 · Login rules (REQ-08). On the web shop these are manual (CAPTCHA); the app has none."""

import pytest
from appium.webdriver.webdriver import WebDriver

from framework.adapters.mobile.screens import CartScreen, CatalogScreen, LoginScreen, ProductScreen
from framework.adapters.mobile.screens.checkout import ShippingScreen
from framework.adapters.mobile.steps import mobile_step
from framework.requirements_marks import covers

pytestmark = [pytest.mark.mobile, pytest.mark.p2]


def _to_login(app: WebDriver) -> LoginScreen:
    """The app asks for a login when a visitor proceeds to checkout."""
    with mobile_step("Add a product and proceed to checkout"):
        CatalogScreen(app).open_product("Sauce Labs Bike Light")
        ProductScreen(app).add_to_cart()
        cart = CartScreen(app)
        cart.open_cart()
        cart.proceed_to_checkout()
    login = LoginScreen(app)
    login.wait_until_loaded()
    return login


@covers("REQ-08")
def test_locked_out_user_cannot_log_in(app: WebDriver) -> None:
    login = _to_login(app)
    login.log_in("alice@example.com", "10203040")
    assert login.password_error() == "Sorry this user has been locked out."


@covers("REQ-08")
def test_login_requires_a_username(app: WebDriver) -> None:
    login = _to_login(app)
    login.log_in("", "10203040")
    assert login.username_error() == "Username is required"


@covers("REQ-08")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,  # only a failed check is the known defect; anything else must surface
    reason="App behaviour read in its source (LoginFragment.loginWithEmail): any non-empty password "
    "is accepted for any user except alice@example.com. Fine for a demo app; a High security "
    "defect in a real one. strict=True: if the app starts checking passwords, this test XPASSes.",
)
def test_wrong_password_is_rejected(app: WebDriver) -> None:
    login = _to_login(app)
    login.log_in("bod@example.com", "definitely-wrong")
    assert not ShippingScreen(app).is_current(), "logged in with a wrong password"
    assert login.password_error(), "no error message for a wrong password"
