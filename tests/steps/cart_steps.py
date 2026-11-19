"""Cart steps. Thin by design: one call to the Store port, then an assertion."""

from pytest_bdd import given, then, when

from framework.domain import Product
from framework.ports import Store
from framework.step_types import parsed


def _table_to_items(datatable: list[list[str]]) -> dict[str, int]:
    header, *rows = datatable
    items: dict[str, int] = {}
    for row in rows:
        record = dict(zip(header, row, strict=True))
        items[record["product"]] = items.get(record["product"], 0) + int(record["quantity"])
    return items


# --- Given -------------------------------------------------------------------
@given("a visitor with an empty cart")
def empty_cart(store: Store) -> None:
    cart = store.cart()
    assert cart.item_count == 0, f"expected an empty cart, got: {cart.describe()}"


@given(parsed('the visitor is viewing the product "{name:Quoted}"'), target_fixture="product")
def viewing_product(store: Store, name: str) -> Product:
    return store.open_product(name)


@given("the cart contains these products:")
def cart_prefilled(store: Store, datatable: list[list[str]]) -> None:
    store.prefill(_table_to_items(datatable))  # setup through the fastest reliable layer


# --- When --------------------------------------------------------------------
@when("they add the product to the cart")
def add_once(store: Store, product: Product) -> None:
    store.add(product.name)


@when(parsed("they add the product to the cart {times:d} times"))
def add_many(store: Store, product: Product, times: int) -> None:
    store.add(product.name, times)


@when("they add these products to the cart:")
def add_table(store: Store, datatable: list[list[str]]) -> None:
    for name, quantity in _table_to_items(datatable).items():
        store.add(name, quantity)


@when(parsed('they add the variant "{variant:Quoted}" to the cart'))
def add_variant(store: Store, product: Product, variant: str) -> None:
    store.add_variant(product.name, variant)


@when(parsed('they remove "{name:Quoted}" from the cart'))
def remove_product(store: Store, name: str) -> None:
    store.remove(name)


@when(parsed('they change the quantity of "{name:Quoted}" to {quantity:d}'))
def change_quantity(store: Store, name: str, quantity: int) -> None:
    store.set_quantity(name, quantity)


@when("they try to add the product to the cart", target_fixture="add_accepted")
def try_add(store: Store, product: Product) -> bool:
    return store.try_add(product.name)


# --- Then --------------------------------------------------------------------
@then(parsed('the cart contains {quantity:d} "{name:Quoted}"'))
def cart_contains(store: Store, quantity: int, name: str) -> None:
    cart = store.cart()
    assert cart.quantity_of(name) == quantity, f"expected {quantity} x {name}, cart: {cart.describe()}"


@then(parsed('the cart contains {quantity:d} "{name:Quoted}" in variant "{variant:Quoted}"'))
def cart_contains_variant(store: Store, quantity: int, name: str, variant: str) -> None:
    cart = store.cart()
    found = [line for line in cart.lines if line.name == name and line.variant == variant]
    assert sum(line.quantity for line in found) == quantity, (
        f"expected {quantity} x {name} ({variant}), cart: {cart.describe()}"
    )


@then(parsed("the cart subtotal equals the product price times {quantity:d}"))
def subtotal_is_price_times(store: Store, product: Product, quantity: int) -> None:
    cart = store.cart()
    expected = product.price * quantity
    assert cart.total == expected, f"expected total {expected}, cart: {cart.describe()}"


@then(parsed('the cart subtotal equals {quantity:d} times the catalogue price of "{name:Quoted}"'))
def subtotal_is_catalogue_price_times(store: Store, quantity: int, name: str) -> None:
    cart = store.cart()
    expected = store.catalogue_price(name) * quantity
    assert cart.total == expected, f"expected total {expected}, cart: {cart.describe()}"


@then(parsed("the cart has {count:d} items in total"))
def total_items(store: Store, count: int) -> None:
    cart = store.cart()
    assert cart.item_count == count, f"expected {count} items, cart: {cart.describe()}"


@then("the product is not added")
def not_added(add_accepted: bool) -> None:
    assert add_accepted is False, "the store accepted a sold-out product"
