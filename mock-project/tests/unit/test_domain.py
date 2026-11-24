from decimal import Decimal

import pytest

from swaglabs.domain import Cart, CartLine, Catalogue, Money, OrderSummary, SortOrder, reference_catalogue


class TestMoney:
    @pytest.mark.parametrize(
        ("text", "amount"),
        [("$29.99", "29.99"), ("Item total: $47.97", "47.97"), ("Tax: $2.40", "2.40"), ("$7", "7.00")],
    )
    def test_parses_amounts_in_labels(self, text: str, amount: str) -> None:
        assert Money.parse(text) == Money(amount)

    def test_rejects_text_without_an_amount(self) -> None:
        with pytest.raises(ValueError, match="no dollar amount"):
            Money.parse("ITEM NOT FOUND")

    def test_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="not an amount"):
            Money("twelve")

    def test_rounds_half_up_to_the_cent(self) -> None:
        assert Money("2.3992") == Money("2.40")
        assert Money("0.005") == Money("0.01")  # banker's rounding would give 0.00

    def test_arithmetic_and_order(self) -> None:
        assert Money("9.99") + Money("0.01") == Money("10")
        assert Money("15.99") * 2 == Money("31.98")
        assert Money("7.99") < Money("9.99")
        assert str(Money("29.9")) == "$29.90"


class TestCatalogue:
    def test_reference_catalogue_has_six_distinct_products(self) -> None:
        catalogue = reference_catalogue()
        assert len(catalogue) == 6
        assert len({p.id for p in catalogue}) == 6

    def test_lookup_ignores_size_suffix(self) -> None:
        catalogue = reference_catalogue()
        assert catalogue.by_name("Sauce Labs Fleece Jacket (XL)").id == 5
        assert catalogue.by_id(4).name == "Sauce Labs Backpack"

    @pytest.mark.parametrize("lookup", ["by_name", "by_id"])
    def test_unknown_product_is_a_key_error(self, lookup: str) -> None:
        with pytest.raises(KeyError):
            getattr(reference_catalogue(), lookup)("Unknown" if lookup == "by_name" else 99)

    def test_slug_matches_button_ids(self) -> None:
        names = {p.name: p.slug for p in reference_catalogue()}
        assert names["Test.allTheThings() T-Shirt (Red)"] == "test.allthethings()-t-shirt-(red)"
        assert names["Sauce Labs Bolt T-Shirt"] == "sauce-labs-bolt-t-shirt"

    def test_image_match_ignores_build_hash(self) -> None:
        backpack = reference_catalogue().by_name("Sauce Labs Backpack")
        assert backpack.shows_image("/static/media/sauce-backpack-1200x1500-CjRW-Djj.jpg")
        assert not backpack.shows_image("/static/media/sl-404-168x168-BhBeXOHy.jpg")

    def test_sort_orders(self) -> None:
        catalogue = reference_catalogue()
        assert catalogue.sorted_names(SortOrder.NAME_ASC)[0] == "Sauce Labs Backpack"
        assert catalogue.sorted_names(SortOrder.NAME_DESC)[0] == "Test.allTheThings() T-Shirt (Red)"
        low = catalogue.sorted_names(SortOrder.PRICE_ASC)
        high = catalogue.sorted_names(SortOrder.PRICE_DESC)
        assert (low[0], low[-1]) == ("Sauce Labs Onesie", "Sauce Labs Fleece Jacket")
        assert (high[0], high[-1]) == ("Sauce Labs Fleece Jacket", "Sauce Labs Onesie")
        # Equal prices ($15.99) keep A-Z order in BOTH directions (stable sort over the default order).
        assert low.index("Sauce Labs Bolt T-Shirt") < low.index("Test.allTheThings() T-Shirt (Red)")
        assert high.index("Sauce Labs Bolt T-Shirt") < high.index("Test.allTheThings() T-Shirt (Red)")

    def test_sort_order_labels_round_trip(self) -> None:
        for order in SortOrder:
            assert SortOrder.from_label(order.label.upper()) is order
        with pytest.raises(ValueError, match="unknown sort order"):
            SortOrder.from_label("Popularity")

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            ({"products": [], "tax_rate": "0.08"}, "no products"),
            (
                {
                    "products": [
                        {"id": 1, "name": "A", "price": "1", "image": "a"},
                        {"id": 2, "name": "A", "price": "2", "image": "b"},
                    ],
                    "tax_rate": "0.08",
                },
                "duplicate",
            ),
        ],
    )
    def test_invalid_catalogue_data_is_refused(self, data: dict[str, object], message: str) -> None:
        with pytest.raises(ValueError, match=message):
            Catalogue.from_json(data)


class TestCartAndOrder:
    def test_cart_totals_and_duplicates(self) -> None:
        cart = Cart.of(
            [
                CartLine("A", 1, Money("29.99")),
                CartLine("B", 2, Money("9.99")),
                CartLine("A", 1, Money("29.99")),
            ]
        )
        assert cart.item_count() == 4
        assert cart.subtotal() == Money("79.96")
        assert cart.duplicates() == ["A"]
        assert cart.names() == ["A", "B", "A"]

    def test_expected_summary_matches_the_shop(self) -> None:
        # Values observed on the live overview page (docs/03-findings.md has the screenshots).
        summary = OrderSummary.expected_for([Money("29.99"), Money("9.99")], Decimal("0.08"))
        assert summary == OrderSummary(Money("39.98"), Money("3.20"), Money("43.18"))
        assert not summary.problems()

    def test_inconsistent_summary_is_reported(self) -> None:
        broken = OrderSummary(Money("10"), Money("0.80"), Money("10.79"))
        assert broken.problems() == ["total $10.79 != subtotal $10.00 + tax $0.80"]
