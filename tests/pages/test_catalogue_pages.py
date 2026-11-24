"""Home, catalogue, product, and search pages."""

import re
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from framework.adapters.web.components import MainMenu
from framework.adapters.web.shop import Shop
from framework.domain import Money

pytestmark = pytest.mark.web


def test_home_shows_featured_products_with_catalogue_prices(shop: Shop) -> None:
    featured = shop.home().open().featured_products()
    assert featured, "the home page shows no products"
    for card in featured:
        assert card.price == shop.catalogue.by_name(card.name).price, card


def test_main_menu_has_every_shop_page(shop: Shop) -> None:
    menu = shop.home().open().menu
    assert set(MainMenu.PAGES) <= set(menu.names()), menu.names()


def test_catalogue_page_matches_catalogue_data(shop: Shop) -> None:
    page = shop.catalog().open()
    cards = {card.name: card for card in page.products()}
    assert sorted(cards) == shop.catalogue.names()
    for name, card in cards.items():
        item = shop.catalogue.by_name(name)
        assert card.handle == item.handle
        assert card.sold_out == (not item.available), name
    assert page.breadcrumb.trail() == ["Home", "Products"]
    assert page.breadcrumb.current() == "Products"


def test_catalogue_card_opens_its_product_page(shop: Shop) -> None:
    shop.catalog().open().open_product("Black heels")
    product = shop.product()
    product.wait_until_loaded()
    assert product.read().name == "Black heels"
    # The demo store's data really maps "Black heels" to this handle (catalogue snapshot).
    expect(shop.page).to_have_url(re.compile(r"/products/flower-print-jeans$"))


def test_product_page_selects_a_variant_and_adds_it(shop: Shop) -> None:
    product = shop.open_product("Noir jacket")
    assert product.option_names() == ["Size", "Color"]
    product.select_variant(shop.catalogue.by_name("Noir jacket").variant("L / Red"))
    product.add_to_cart()
    product.header.expect_cart_count(1)


def test_sold_out_product_cannot_be_added(shop: Shop) -> None:
    product = shop.open_product("Brown Shades")
    assert product.read().available is False
    assert product.is_sold_out()


def test_search_lists_matching_products(shop: Shop) -> None:
    results = shop.search().open_for("jacket").results()
    assert {card.name for card in results} >= {"Grey jacket", "Noir jacket"}
    assert all(card.price > Money(Decimal(0)) for card in results)


# One nonsense token: Shopify search splits "zzzz-no-such-product" into words, and "product",
# "no", "such" match real products (seen 2026-11-19: 5 results, "Showing results for ...").
NO_MATCH = "zzqqxx"


def test_search_without_matches_says_so(shop: Shop) -> None:
    page = shop.search().open_for(NO_MATCH)
    assert page.has_no_results(), f"the page says: {page.keyword_message()!r}"
    assert page.results() == []


def test_header_search_box_leads_to_results(shop: Shop) -> None:
    shop.home().open().header.search("sandals")
    assert "Bronze sandals" in shop.search().titles()
