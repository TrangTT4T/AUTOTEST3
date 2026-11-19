from decimal import Decimal

import pytest

from framework.domain import Money


@pytest.mark.parametrize(
    ("text", "expected"),
    [("£55.00", "55.00"), ("£1,055.50", "1055.50"), (" £39.99 ", "39.99"), ("Total £230.00", "230.00")],
)
def test_parse_reads_the_amount(text: str, expected: str) -> None:
    assert Money.parse(text) == Money(Decimal(expected))


def test_parse_rejects_text_without_digits() -> None:
    with pytest.raises(ValueError, match="no amount"):
        Money.parse("Sold Out")


def test_minor_units_are_pence() -> None:
    assert Money.from_minor_units(5500) == Money(Decimal("55.00"))


def test_arithmetic_is_exact() -> None:
    assert Money(Decimal("0.10")) + Money(Decimal("0.20")) == Money(Decimal("0.30"))
    assert Money(Decimal("39.99")) * 3 == Money(Decimal("119.97"))
    assert 2 * Money(Decimal("55")) == Money(Decimal("110.00"))


def test_currencies_do_not_mix() -> None:
    with pytest.raises(ValueError, match="cannot combine"):
        _ = Money(Decimal(1), "GBP") + Money(Decimal(1), "USD")


def test_str_uses_the_currency_symbol() -> None:
    assert str(Money(Decimal("55"))) == "£55.00"
    assert str(Money(Decimal("5"), "JPY")) == "5.00 JPY"
