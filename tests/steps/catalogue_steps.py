"""Catalogue steps: search, product details, sold-out products."""

import pytest
from pytest_bdd import given, then, when

from framework.domain import Product, ProductCard
from framework.ports import Store
from framework.step_types import parsed


@given("the visitor is viewing a sold-out product", target_fixture="product")
def viewing_sold_out(store: Store) -> Product:
    name = store.find_sold_out_product()  # chosen at runtime, never hard-coded
    if name is None:
        pytest.skip("No sold-out product exists in the store right now")
    product = store.open_product(name)
    assert not product.available, f"{name!r} is listed as sold out but its page offers Add to Cart"
    return product


@when(parsed('the visitor searches for "{keyword:Quoted}"'), target_fixture="results")
def search(store: Store, keyword: str) -> list[str]:
    return store.search(keyword)


@then(parsed("at least {count:d} products are found"))
def at_least(results: list[str], count: int) -> None:
    assert len(results) >= count, f"expected at least {count} results, got {results}"


@then(parsed('every result mentions "{keyword:Quoted}"'))
def every_result_mentions(results: list[str], keyword: str) -> None:
    unrelated = [r for r in results if keyword.lower() not in r.lower()]
    assert not unrelated, f"results without {keyword!r}: {unrelated}"


@then("no products are found")
def nothing_found(results: list[str]) -> None:
    assert results == [], f"expected no results, got {results}"


@then(parsed('the product page shows the name "{name:Quoted}"'))
def shows_name(product: Product, name: str) -> None:
    assert product.name == name


@then("the product page price matches the catalogue price")
def price_matches_catalogue(store: Store, product: Product) -> None:
    expected = store.catalogue_price(product.name)
    assert product.price == expected, f"page shows {product.price}, catalogue says {expected}"


@when("the visitor browses the catalogue", target_fixture="listing")
def browse_catalogue(store: Store) -> list[ProductCard]:
    return store.catalogue_listing()


@then("every product in the store is listed with its catalogue price")
def every_product_listed(store: Store, listing: list[ProductCard]) -> None:
    catalogue = store.catalogue_data()
    shown = {card.name: card.price for card in listing}
    expected = {name: catalogue.by_name(name).price for name in catalogue.names()}
    assert shown == expected, f"catalogue page {shown} vs data {expected}"


@then(parsed('exactly the sold-out products are labelled "{label:Quoted}"'))
def sold_out_labels(store: Store, listing: list[ProductCard], label: str) -> None:
    labelled = sorted(card.name for card in listing if card.sold_out)
    expected = sorted(item.name for item in store.catalogue_data().sold_out())
    assert labelled == expected, f"{label!r} shown on {labelled}, but sold out in data: {expected}"
