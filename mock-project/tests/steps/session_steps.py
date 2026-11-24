"""Steps for logging in, sessions, logout and the side menu."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from swaglabs.app import SESSION_COOKIE, SwagLabs
from tests.steps.memo import Memo, quoted

VALID, EMPTY = "(valid)", "(empty)"


def _value(shop: SwagLabs, token: str) -> str:
    """Feature files never contain the password: ``(valid)`` stands for it, ``(empty)`` for ''."""
    return {VALID: shop.settings.password, EMPTY: ""}.get(token, token)


@when("I log in as the persona under test")
def log_in_as_persona(shop: SwagLabs) -> None:
    shop.log_in_with_form(shop.settings.persona.value, shop.settings.password)


@when(parsers.parse('I log in with username "{username}" and password "{password}"'))
def log_in_with(shop: SwagLabs, username: str, password: str) -> None:
    shop.login_page().log_in(_value(shop, username), _value(shop, password))


@then("I see the products page")
def see_products(shop: SwagLabs) -> None:
    shop.inventory().wait_until_loaded()


@then("the session belongs to the persona under test")
def session_is_persona(shop: SwagLabs) -> None:
    assert shop.session_user() == shop.settings.persona.value


@then("the session cookie is the one the quick-login shortcut sets")
def cookie_matches_shortcut(shop: SwagLabs) -> None:
    # Contract for SwagLabs.start_session(): if the shop renames or re-shapes its session,
    # this fails and the shortcut is fixed before it silently tests the wrong thing.
    assert shop.session_user() == shop.settings.persona.value, f"expected cookie {SESSION_COOKIE!r}"


@then("I stay on the login page")
@then("I see the login page")
def see_login(shop: SwagLabs) -> None:
    shop.login_page().wait_until_loaded()


@then(parsers.parse('I see the login error "{message}"'))
def see_login_error(shop: SwagLabs, message: str) -> None:
    shop.login_page().expect_error(message)


@then("the username and password fields are marked invalid")
def fields_invalid(shop: SwagLabs) -> None:
    shop.login_page().expect_fields_marked_invalid()


@when("I close the login error")
def close_error(shop: SwagLabs) -> None:
    shop.login_page().close_error()


@then("no login error is shown")
def no_error(shop: SwagLabs) -> None:
    shop.login_page().expect_no_error()


@when(parsers.parse('I open "{path}" without logging in'))
def open_without_session(shop: SwagLabs, path: str) -> None:
    shop.visit(path)


@when("I log out")
def log_out(shop: SwagLabs) -> None:
    shop.header.open_menu().log_out()
    shop.login_page().wait_until_loaded()


@then(parsers.parse('opening "{path}" sends me back to the login page'))
def protected_after_logout(shop: SwagLabs, path: str) -> None:
    shop.visit(path)
    login = shop.login_page()
    login.wait_until_loaded()
    login.expect_error(f"Epic sadface: You can only access '{path}' when you are logged in.")


@when("I go back in the browser")
def go_back(shop: SwagLabs) -> None:
    shop.go_back()


@when("I reset the app state from the menu")
def reset_state(shop: SwagLabs) -> None:
    menu = shop.header.open_menu()
    menu.reset_app_state()
    menu.close()


@then('every product offers "Add to cart"')
def every_product_offers_add(shop: SwagLabs) -> None:
    inventory = shop.inventory()
    for product in shop.catalogue:
        inventory.expect_offers_add(product)


@when("I tap the menu button")
def tap_menu(shop: SwagLabs, memo: Memo) -> None:
    memo.menu = shop.header.open_menu(touch=True)


@then(parsers.re(r"the menu offers (?P<entries>\".+\")"))
def menu_offers(memo: Memo, entries: str) -> None:
    assert memo.menu is not None, "open the menu first"
    assert memo.menu.entries() == quoted(entries)


@when("I close the menu")
def close_menu(memo: Memo) -> None:
    assert memo.menu is not None, "open the menu first"
    memo.menu.close()


@then("the products page is usable again")
def products_usable(shop: SwagLabs) -> None:
    product = shop.catalogue.by_name("Sauce Labs Backpack")
    inventory = shop.inventory()
    inventory.tap_add(product)
    inventory.expect_in_cart(product)
