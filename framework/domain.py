"""Domain model: the shop's concepts as immutable, typed values.

Steps and assertions work with these objects, never with raw HTML text or
JSON dictionaries. Every adapter (fake, web, later mobile) returns them.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from framework.errors import DataUnavailableError

_CENT = Decimal("0.01")
_SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€"}


@dataclass(frozen=True, order=True)
class Money:
    """An exact amount of money. Never use float for money."""

    amount: Decimal
    currency: str = "GBP"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(self.amount).quantize(_CENT))

    @classmethod
    def parse(cls, text: str, currency: str = "GBP") -> Money:
        """'£1,055.00' -> Money(1055.00)."""
        digits = re.sub(r"[^\d.]", "", text)
        if not digits:
            raise ValueError(f"no amount found in {text!r}")
        return cls(Decimal(digits), currency)

    @classmethod
    def from_minor_units(cls, minor: int, currency: str = "GBP") -> Money:
        """Shopify cart JSON uses pence: 5500 -> £55.00."""
        return cls(Decimal(minor) / 100, currency)

    @classmethod
    def zero(cls, currency: str = "GBP") -> Money:
        return cls(Decimal(0), currency)

    def __add__(self, other: Money) -> Money:
        self._same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, quantity: int) -> Money:
        return Money(self.amount * quantity, self.currency)

    __rmul__ = __mul__

    def _same_currency(self, other: Money) -> None:
        if other.currency != self.currency:
            raise ValueError(f"cannot combine {self.currency} and {other.currency}")

    def __str__(self) -> str:
        symbol = _SYMBOLS.get(self.currency)
        return f"{symbol}{self.amount}" if symbol else f"{self.amount} {self.currency}"


@dataclass(frozen=True)
class Variant:
    id: int
    title: str
    price: Money
    available: bool


@dataclass(frozen=True)
class CatalogueItem:
    name: str
    handle: str
    variants: tuple[Variant, ...]

    @property
    def available(self) -> bool:
        return any(v.available for v in self.variants)

    @property
    def price(self) -> Money:
        return self.variants[0].price

    def variant(self, title: str) -> Variant:
        for variant in self.variants:
            if variant.title == title:
                return variant
        raise DataUnavailableError(
            f"{self.name!r} has no variant {title!r}; it has: {[v.title for v in self.variants]}"
        )

    def first_available_variant(self) -> Variant:
        for variant in self.variants:
            if variant.available:
                return variant
        raise DataUnavailableError(f"{self.name!r} has no available variant")


class Catalogue:
    """Product data from the shop's data layer (``/products.json``)."""

    def __init__(self, items: Iterable[CatalogueItem], currency: str = "GBP") -> None:
        self.currency = currency  # every price in this catalogue uses it
        self._by_name = {item.name: item for item in items}
        self._by_handle = {item.handle: item for item in self._by_name.values()}

    @classmethod
    def from_products_json(cls, data: Mapping[str, Any]) -> Catalogue:
        """Shopify's /products.json, or a snapshot in the same shape (``currency`` defaults to GBP)."""
        currency = str(data.get("currency", "GBP"))
        items = (
            CatalogueItem(
                name=p["title"],
                handle=p["handle"],
                variants=tuple(
                    Variant(v["id"], v["title"], Money(Decimal(v["price"]), currency), bool(v["available"]))
                    for v in p["variants"]
                ),
            )
            for p in data["products"]
        )
        return cls(items, currency=currency)

    def by_name(self, name: str) -> CatalogueItem:
        try:
            return self._by_name[name]
        except KeyError:
            raise DataUnavailableError(
                f"no product named {name!r}; the store has: {sorted(self._by_name)}"
            ) from None

    def by_handle(self, handle: str) -> CatalogueItem:
        try:
            return self._by_handle[handle]
        except KeyError:
            raise DataUnavailableError(f"no product with handle {handle!r}") from None

    def sold_out(self) -> list[CatalogueItem]:
        return [item for item in self._by_name.values() if not item.available]

    def names(self) -> list[str]:
        return sorted(self._by_name)


@dataclass(frozen=True)
class Product:
    """What a visitor sees on a product page."""

    name: str
    price: Money
    available: bool


@dataclass(frozen=True)
class CartLine:
    name: str
    variant: str
    quantity: int
    line_total: Money


@dataclass(frozen=True)
class Cart:
    """An immutable snapshot of the cart at one moment."""

    lines: tuple[CartLine, ...]
    total: Money

    @classmethod
    def empty(cls, currency: str = "GBP") -> Cart:
        return cls((), Money.zero(currency))

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    def quantity_of(self, name: str) -> int:
        """Total quantity of one product across all its variants."""
        return sum(line.quantity for line in self.lines if line.name == name)

    def quantities(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for line in self.lines:
            result[line.name] = result.get(line.name, 0) + line.quantity
        return result

    def describe(self) -> str:
        """Human-readable summary for assertion messages."""
        if not self.lines:
            return "empty cart"
        items = ", ".join(f"{l.quantity} x {l.name} ({l.variant})" for l in self.lines)
        return f"{items}; total {self.total}"


@dataclass(frozen=True)
class ProductCard:
    """One tile in a product grid (home page, catalogue, search results)."""

    name: str
    price: Money
    sold_out: bool
    handle: str


@dataclass(frozen=True)
class OrderSummary:
    """The checkout page's summary. Read-only: the framework never pays."""

    lines: tuple[CartLine, ...]
    subtotal: Money
    total: Money
    included_tax: Money | None

    def quantities(self) -> dict[str, int]:
        return Cart(self.lines, self.subtotal).quantities()


@dataclass(frozen=True)
class ArticleSummary:
    """One entry in the blog list."""

    title: str
    date: str
    handle: str


@dataclass(frozen=True)
class Customer:
    """Account data for sign-up and login forms."""

    first_name: str
    last_name: str
    email: str
    password: str
