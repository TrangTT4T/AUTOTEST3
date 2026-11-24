"""Steps for the catalogue: listing, prices, images, sorting and product pages."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from swaglabs.app import SwagLabs
from swaglabs.domain import SortOrder
from tests.steps.memo import Memo


@then(parsers.parse("the catalogue lists the {count:d} reference products"))
def lists_reference_products(shop: SwagLabs, count: int) -> None:
    assert len(shop.catalogue) == count, "the feature and the reference catalogue disagree"
    shop.inventory().expect_names(shop.catalogue.sorted_names(SortOrder.NAME_ASC))


@then("every card shows its product's reference price")
def cards_show_reference_prices(shop: SwagLabs) -> None:
    wrong = [
        f"{card.name}: shows {card.price}, reference {shop.catalogue.by_name(card.name).price}"
        for card in shop.inventory().read_cards()
        if card.price != shop.catalogue.by_name(card.name).price
    ]
    assert not wrong, "wrong prices:\n  " + "\n  ".join(wrong)


@then("every card shows its product's own image")
def cards_show_own_images(shop: SwagLabs) -> None:
    wrong = [
        f"{card.name}: shows {card.image_src.rsplit('/', 1)[-1]}"
        for card in shop.inventory().read_cards()
        if not shop.catalogue.by_name(card.name).shows_image(card.image_src)
    ]
    assert not wrong, "wrong images:\n  " + "\n  ".join(wrong)


@when(parsers.parse('I sort the products by "{label}"'))
def sort_by(shop: SwagLabs, label: str) -> None:
    order = SortOrder.from_label(label)
    inventory = shop.inventory()
    expected_first = shop.catalogue.sorted_names(order)[0]
    # Timed until the visible outcome: the first card is the one this order puts first.
    with shop.perf.measure("sort"):
        inventory.sort_by(order)
        inventory.expect_first_name(expected_first)


@then(parsers.parse('the products are listed in "{label}" order'))
def listed_in_order(shop: SwagLabs, label: str) -> None:
    shop.inventory().expect_names(shop.catalogue.sorted_names(SortOrder.from_label(label)))


@then("no error dialog appeared")
def no_dialog(shop: SwagLabs) -> None:
    assert not shop.monitor.dialogs, f"unexpected dialog(s): {shop.monitor.dialogs}"


@when(parsers.parse('I open "{name}" from its card'))
def open_from_card(shop: SwagLabs, memo: Memo, name: str) -> None:
    inventory = shop.inventory()
    memo.card = next(card for card in inventory.read_cards() if card.name == name)
    with shop.perf.measure("open-product"):
        inventory.open_product(name)
        shop.product().wait_until_loaded()


@then("the product page shows the same name, price and image as the card")
def product_matches_card(shop: SwagLabs, memo: Memo) -> None:
    assert memo.card is not None, "open a product from its card first"
    page = shop.product()
    page.expect_name(memo.card.name)  # retrying: the name settles first
    shown = page.read()
    assert shown.price == memo.card.price, f"card says {memo.card.price}, product page says {shown.price}"
    product = shop.catalogue.by_name(memo.card.name)
    assert product.shows_image(shown.image_src) == product.shows_image(memo.card.image_src), (
        f"different pictures: card {memo.card.image_src}, page {shown.image_src}"
    )


@when("I go back to the products")
def back_to_products(shop: SwagLabs) -> None:
    shop.product().back_to_products()
    shop.inventory().wait_until_loaded()
