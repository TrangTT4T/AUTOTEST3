import re
from decimal import Decimal

import pytest

from framework.adapters.web.store import WebStore
from framework.domain import Cart, CartLine, Money
from framework.errors import CartInconsistencyError


def _cart(qty: int, total: str) -> Cart:
    return Cart((CartLine("Grey jacket", "Grey jacket", qty, Money(Decimal(total))),), Money(Decimal(total)))


def test_matching_layers_pass() -> None:
    WebStore._check_consistent(_cart(2, "110"), _cart(2, "110"), header_count=2)


@pytest.mark.parametrize(
    ("ui", "data", "header", "message"),
    [
        (_cart(1, "55"), _cart(2, "110"), 2, "quantities"),
        (_cart(2, "100"), _cart(2, "110"), 2, "total"),
        (_cart(2, "110"), _cart(2, "110"), 1, "header 'My Cart (1)'"),
    ],
)
def test_disagreement_is_a_product_defect(ui: Cart, data: Cart, header: int, message: str) -> None:
    with pytest.raises(CartInconsistencyError, match=re.escape(message)):
        WebStore._check_consistent(ui, data, header)
