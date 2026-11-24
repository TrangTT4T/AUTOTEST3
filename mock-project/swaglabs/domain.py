"""Business model of the shop, and the oracles the scenarios check against.

Pure Python, no browser: unit-tested in tests/unit/test_domain.py. Page objects translate
what they read on screen into these types, so steps compare business values
(``Money("29.99")``), never strings scraped from the page.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum
from functools import cache
from importlib import resources
from typing import Self

CENT = Decimal("0.01")
_MONEY = re.compile(r"\$\s*(?P<amount>\d+(?:\.\d+)?)")
_SIZE_SUFFIX = re.compile(r" \((?:XS|S|M|L|XL|XXL)\)$")


@dataclass(frozen=True, order=True)
class Money:
    """An amount in US dollars, exact to the cent (Decimal: no float rounding errors)."""

    amount: Decimal

    def __init__(self, amount: Decimal | str | int) -> None:
        try:
            value = Decimal(amount)
        except InvalidOperation as error:
            raise ValueError(f"not an amount: {amount!r}") from error
        object.__setattr__(self, "amount", value.quantize(CENT, rounding=ROUND_HALF_UP))

    @classmethod
    def parse(cls, text: str) -> Self:
        """The amount in a label such as ``'$29.99'`` or ``'Item total: $47.97'``."""
        match = _MONEY.search(text)
        if match is None:
            raise ValueError(f"no dollar amount in {text!r}")
        return cls(match["amount"])

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __mul__(self, factor: Decimal | int) -> Money:
        return Money(self.amount * factor)

    def __str__(self) -> str:
        return f"${self.amount}"


ZERO = Money("0")


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: Money
    image: str  # stable start of the image file name; the rest is a build hash

    @property
    def slug(self) -> str:
        """The suffix of the product's button ids: ``add-to-cart-<slug>`` / ``remove-<slug>``."""
        return self.name.lower().replace(" ", "-")

    def shows_image(self, src: str) -> bool:
        """True when an <img src> is this product's picture (whatever the build hash)."""
        file_name = src.rsplit("/", 1)[-1]
        return file_name.split("-1200x", 1)[0] == self.image


@dataclass(frozen=True)
class Catalogue:
    """The reference catalogue: what the shop SHOULD show (the oracle)."""

    products: tuple[Product, ...]
    tax_rate: Decimal

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        rows = data["products"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("catalogue has no products")
        products = tuple(
            Product(int(row["id"]), str(row["name"]), Money(str(row["price"])), str(row["image"]))
            for row in rows
        )
        names = [p.name for p in products]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate product names in catalogue: {names}")
        return cls(products, Decimal(str(data["tax_rate"])))

    def __iter__(self) -> Iterator[Product]:
        return iter(self.products)

    def __len__(self) -> int:
        return len(self.products)

    def by_name(self, name: str) -> Product:
        """The product called ``name``; a size suffix (``'... (XL)'``) is ignored."""
        base = _SIZE_SUFFIX.sub("", name)
        for product in self.products:
            if product.name == base:
                return product
        raise KeyError(f"no product named {name!r} in the catalogue")

    def by_id(self, product_id: int) -> Product:
        for product in self.products:
            if product.id == product_id:
                return product
        raise KeyError(f"no product with id {product_id}")

    def names(self) -> list[str]:
        return [p.name for p in self.products]

    def sorted_names(self, order: SortOrder) -> list[str]:
        """The names in the order the shop must show for ``order``.

        Equal prices keep name order (A to Z) in both price orders: the shop's sort is stable
        over its default order.
        """
        if order is SortOrder.NAME_ASC:
            return sorted(self.names())
        if order is SortOrder.NAME_DESC:
            return sorted(self.names(), reverse=True)
        sign = 1 if order is SortOrder.PRICE_ASC else -1
        return [p.name for p in sorted(self.products, key=lambda p: (sign * p.price.amount, p.name))]


@cache
def reference_catalogue() -> Catalogue:
    raw = resources.files("swaglabs").joinpath("data/catalogue.json").read_text(encoding="utf-8")
    return Catalogue.from_json(json.loads(raw))


class SortOrder(Enum):
    """The four options of the sort drop-down; the member value is the <option> value."""

    NAME_ASC = "az"
    NAME_DESC = "za"
    PRICE_ASC = "lohi"
    PRICE_DESC = "hilo"

    @property
    def label(self) -> str:
        return _SORT_LABELS[self]

    @classmethod
    def from_label(cls, label: str) -> SortOrder:
        for order, text in _SORT_LABELS.items():
            if text.lower() == label.lower():
                return order
        raise ValueError(f"unknown sort order {label!r}; one of {list(_SORT_LABELS.values())}")


_SORT_LABELS = {
    SortOrder.NAME_ASC: "Name (A to Z)",
    SortOrder.NAME_DESC: "Name (Z to A)",
    SortOrder.PRICE_ASC: "Price (low to high)",
    SortOrder.PRICE_DESC: "Price (high to low)",
}


@dataclass(frozen=True)
class CartLine:
    name: str
    quantity: int
    price: Money


@dataclass(frozen=True)
class Cart:
    lines: tuple[CartLine, ...]

    @classmethod
    def of(cls, lines: Iterable[CartLine]) -> Self:
        return cls(tuple(lines))

    def names(self) -> list[str]:
        return [line.name for line in self.lines]

    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    def subtotal(self) -> Money:
        total = ZERO
        for line in self.lines:
            total += line.price * line.quantity
        return total

    def duplicates(self) -> list[str]:
        """Names that appear on more than one line (a cart must merge them)."""
        names = self.names()
        return sorted({n for n in names if names.count(n) > 1})


@dataclass(frozen=True)
class OrderSummary:
    """The three amounts on the checkout overview."""

    subtotal: Money
    tax: Money
    total: Money

    @classmethod
    def expected_for(cls, prices: Iterable[Money], tax_rate: Decimal) -> Self:
        """What the overview must show: tax is rounded half-up to the cent, then added."""
        subtotal = ZERO
        for price in prices:
            subtotal += price
        tax = subtotal * tax_rate
        return cls(subtotal, tax, subtotal + tax)

    def problems(self) -> list[str]:
        """Internal consistency, independent of the oracle: total = subtotal + tax."""
        if self.subtotal + self.tax != self.total:
            return [f"total {self.total} != subtotal {self.subtotal} + tax {self.tax}"]
        return []
