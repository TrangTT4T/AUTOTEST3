"""The fake must behave like the real store, or offline runs prove nothing."""

from decimal import Decimal

import pytest

from framework.adapters.fake import FakeStore
from framework.domain import Money
from framework.errors import AmbiguousTargetError
from framework.ports import Store


def test_fake_implements_the_store_port() -> None:
    assert isinstance(FakeStore.from_snapshot(), Store)


def test_sold_out_products_cannot_be_added() -> None:
    store = FakeStore.from_snapshot()
    assert store.try_add("Brown Shades") is False
    assert store.cart().item_count == 0


def test_quantity_zero_removes_the_line_like_shopify() -> None:
    store = FakeStore.from_snapshot()
    store.prefill({"Grey jacket": 2})
    store.set_quantity("Grey jacket", 0)
    assert store.cart().quantity_of("Grey jacket") == 0


def test_cart_total_uses_catalogue_prices() -> None:
    store = FakeStore.from_snapshot()
    store.prefill({"Grey jacket": 1, "Bronze sandals": 2})
    assert store.cart().total == Money(Decimal("134.98"))


def test_variants_are_separate_cart_lines() -> None:
    store = FakeStore.from_snapshot()
    store.add_variant("Noir jacket", "L / Red")
    store.add_variant("Noir jacket", "S / Blue", 2)
    cart = store.cart()
    assert cart.quantity_of("Noir jacket") == 3
    assert {(line.variant, line.quantity) for line in cart.lines} == {("L / Red", 1), ("S / Blue", 2)}


def test_catalogue_listing_labels_sold_out_products() -> None:
    listing = FakeStore.from_snapshot().catalogue_listing()
    assert sorted(card.name for card in listing if card.sold_out) == ["Brown Shades", "White sandals"]


def test_checkout_summary_mirrors_the_cart_with_uk_vat() -> None:
    store = FakeStore.from_snapshot()
    store.prefill({"Grey jacket": 2})
    store.go_to_checkout()
    summary = store.checkout_summary()
    assert summary.quantities() == {"Grey jacket": 2}
    assert summary.total == Money(Decimal("110.00"))
    assert summary.included_tax == Money(Decimal("18.33"))  # observed live for £110


@pytest.mark.parametrize(
    "variants",
    [[], ["L / Red", "S / Blue"]],
    ids=["not-in-cart", "two-variants"],
)
def test_set_quantity_needs_exactly_one_line(variants: list[str]) -> None:
    """Like the web cart: one locator must mean one line, never "whichever comes first"."""
    store = FakeStore.from_snapshot()
    for variant in variants:
        store.add_variant("Noir jacket", variant)
    with pytest.raises(AmbiguousTargetError, match=f"has {len(variants)} lines"):
        store.set_quantity("Noir jacket", 3)
    assert store.cart().quantity_of("Noir jacket") == len(variants)  # nothing changed
