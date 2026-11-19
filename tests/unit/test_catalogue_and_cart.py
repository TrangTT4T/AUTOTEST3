from decimal import Decimal

import pytest

from framework.domain import Cart, CartLine, Catalogue, Money
from framework.errors import DataUnavailableError


def test_snapshot_matches_the_live_store_facts(catalogue_snapshot: Catalogue) -> None:
    assert catalogue_snapshot.by_name("Grey jacket").price == Money(Decimal("55.00"))
    assert catalogue_snapshot.by_name("Black heels").handle == "flower-print-jeans"
    assert {item.name for item in catalogue_snapshot.sold_out()} == {"Brown Shades", "White sandals"}


def test_unknown_product_lists_what_exists(catalogue_snapshot: Catalogue) -> None:
    with pytest.raises(DataUnavailableError, match="Grey jacket"):
        catalogue_snapshot.by_name("Pink jacket")


def test_sold_out_product_has_no_available_variant(catalogue_snapshot: Catalogue) -> None:
    with pytest.raises(DataUnavailableError):
        catalogue_snapshot.by_name("Brown Shades").first_available_variant()


def _line(name: str, variant: str, qty: int, total: str) -> CartLine:
    return CartLine(name, variant, qty, Money(Decimal(total)))


def test_cart_adds_up_variants_of_one_product() -> None:
    cart = Cart(
        (
            _line("Noir jacket", "S / Blue", 1, "60"),
            _line("Noir jacket", "M / Blue", 2, "120"),
            _line("Grey jacket", "Grey jacket", 1, "55"),
        ),
        Money(Decimal("235")),
    )
    assert cart.quantity_of("Noir jacket") == 3
    assert cart.item_count == 4
    assert cart.quantities() == {"Noir jacket": 3, "Grey jacket": 1}
    assert cart.describe() == (
        "1 x Noir jacket (S / Blue), 2 x Noir jacket (M / Blue), 1 x Grey jacket (Grey jacket); total £235.00"
    )


def test_empty_cart() -> None:
    assert Cart.empty().item_count == 0
    assert Cart.empty().describe() == "empty cart"


def test_variant_lookup_by_title(catalogue_snapshot: Catalogue) -> None:
    noir = catalogue_snapshot.by_name("Noir jacket")
    assert noir.variant("L / Red").id == 7805238401
    with pytest.raises(DataUnavailableError, match="S / Blue"):
        noir.variant("XL / Green")
