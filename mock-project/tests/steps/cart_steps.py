"""Steps for adding, removing and checking cart contents, in one tab or two."""

from __future__ import annotations

from pytest_bdd import given, parsers, then, when

from swaglabs.app import SwagLabs
from swaglabs.domain import CartLine, Money
from tests.steps.memo import Memo


@when(parsers.parse('I add "{name}" to the cart'))
def add_to_cart(shop: SwagLabs, name: str) -> None:
    product = shop.catalogue.by_name(name)
    inventory = shop.inventory()
    with shop.perf.measure("add-to-cart"):
        inventory.add(product)
        inventory.expect_in_cart(product)


@when(parsers.parse('I tap Add to cart for "{name}"'))
def tap_add(shop: SwagLabs, name: str) -> None:
    product = shop.catalogue.by_name(name)
    inventory = shop.inventory()
    with shop.perf.measure("add-to-cart"):
        inventory.tap_add(product)
        inventory.expect_in_cart(product)


@when("I add every product to the cart")
def add_every_product(shop: SwagLabs) -> None:
    for product in shop.catalogue:
        add_to_cart(shop, product.name)


@then("the cart holds exactly:")
def cart_holds_exactly(shop: SwagLabs, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    assert header == ["product", "quantity", "price"], f"unexpected table header {header}"
    expected = [CartLine(name, int(quantity), Money.parse(price)) for name, quantity, price in rows]
    shop.header.open_cart()
    cart = shop.cart()
    cart.wait_until_loaded()
    cart.expect_names([line.name for line in expected])  # retrying; then one exact comparison
    actual = cart.read()
    assert list(actual.lines) == expected
    assert not actual.duplicates()


@then("the stored cart holds every product")
def stored_cart_holds_all(shop: SwagLabs) -> None:
    shop.eventually_stored_cart([p.id for p in shop.catalogue])


@when(parsers.parse('I remove "{name}" on the catalogue page'))
def remove_on_catalogue(shop: SwagLabs, name: str) -> None:
    product = shop.catalogue.by_name(name)
    inventory = shop.inventory()
    inventory.remove(product)
    inventory.expect_offers_add(product)


@then(parsers.parse('the stored cart holds only "{name}"'))
@then(parsers.parse('the stored cart eventually holds only "{name}"'))
def stored_cart_only(shop: SwagLabs, name: str) -> None:
    shop.eventually_stored_cart([shop.catalogue.by_name(name).id])


@when(parsers.parse('I remove "{name}" on the cart page'))
def remove_on_cart_page(shop: SwagLabs, name: str) -> None:
    shop.cart().remove(shop.catalogue.by_name(name))


@when(parsers.parse('I double-click Add to cart for "{name}"'))
def double_click_add(shop: SwagLabs, name: str) -> None:
    shop.inventory().double_click_add(shop.catalogue.by_name(name))


@then(parsers.parse('the stored cart holds "{name}" at most once'))
def stored_at_most_once(shop: SwagLabs, name: str) -> None:
    product_id = shop.catalogue.by_name(name).id
    ids = shop.stored_cart_ids()
    assert ids.count(product_id) <= 1, f"stored cart {ids} holds {name} {ids.count(product_id)} times"


@then("the cart badge agrees with the stored cart")
def badge_agrees(shop: SwagLabs) -> None:
    # Two sources of truth that update separately: wait until they agree (eventual consistency).
    shop.eventually(
        lambda: (shop.header.cart_count(), len(set(shop.stored_cart_ids()))),
        lambda pair: pair[0] == pair[1],
        "badge count and number of stored products should agree",
    )


@given("a second tab shows the cart")
def second_tab(shop: SwagLabs, memo: Memo) -> None:
    memo.second_tab = shop.new_tab()
    memo.second_tab.cart().open()


@when(parsers.parse('I remove "{name}" in the second tab'))
def remove_in_second_tab(memo: Memo, name: str) -> None:
    assert memo.second_tab is not None, "open a second tab first"
    tab = memo.second_tab
    product = tab.catalogue.by_name(name)
    tab.cart().remove(product)
    tab.cart().expect_names([n for n in (p.name for p in memo.cart_products) if n != name])


@then(parsers.parse("after a reload the first tab's badge shows {count:d}"))
def first_tab_after_reload(shop: SwagLabs, count: int) -> None:
    shop.reload()
    shop.header.expect_cart_count(count)
