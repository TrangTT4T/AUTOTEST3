"""Steps for asynchronous content: spinner, lazy loading and the auto-rotating slider."""

from __future__ import annotations

import time

from pytest_bdd import parsers, then, when

from swaglabs.app import SwagLabs
from swaglabs.domain import Tile
from tests.steps.memo import Memo

SAMPLE_EVERY_MS = 250


def _wrong_tiles(shop: SwagLabs, tiles: list[Tile]) -> list[str]:
    wrong = []
    for tile in tiles:
        try:
            product = shop.catalogue.by_name(tile.name or "")
        except KeyError:
            wrong.append(f"{tile.id}: unknown product {tile.name!r}")
            continue
        if tile.price != product.price:
            wrong.append(f"{tile.id}: {tile.name} at {tile.price}, reference {product.price}")
    return wrong


@when("I open the spinner catalogue")
def open_spinner(shop: SwagLabs) -> None:
    shop.spinner_catalogue().open()


@then("the products appear once the spinner has gone")
def spinner_done(shop: SwagLabs) -> None:
    shop.spinner_catalogue().wait_for_products()


@then("every tile shows a reference product at its reference price")
def tiles_match_reference(shop: SwagLabs) -> None:
    tiles = shop.spinner_catalogue().read_tiles()
    assert len(tiles) == len(shop.catalogue), f"{len(tiles)} tiles, expected {len(shop.catalogue)}"
    wrong = _wrong_tiles(shop, tiles)
    assert not wrong, "\n  ".join(["wrong tiles:", *wrong])


@when("I open the lazy-loading catalogue")
def open_lazy(shop: SwagLabs) -> None:
    shop.lazy_catalogue().open()


@when(parsers.parse("I scroll down until at least {count:d} products have loaded"))
def scroll_until(shop: SwagLabs, count: int) -> None:
    page = shop.lazy_catalogue()

    def scroll_and_count_loaded() -> int:
        # Scrolling is the one action inside this retry loop: it is what a reader repeats, and
        # one screen too many does no harm. Everything the check decides on is a READ.
        page.scroll_one_screen()
        return sum(not t.loading for t in page.read_tiles())

    shop.eventually(scroll_and_count_loaded, lambda n: n >= count, f"at least {count} tiles should load")


@then("every tile on screen finishes loading")
def tiles_on_screen_load(shop: SwagLabs) -> None:
    shop.eventually(
        shop.lazy_catalogue().read_tiles,
        lambda tiles: not any(t.loading and t.on_screen for t in tiles),
        "no tile on screen should still be a placeholder",
    )


@then("every loaded tile shows a reference product at its reference price")
def loaded_tiles_match(shop: SwagLabs) -> None:
    loaded = [t for t in shop.lazy_catalogue().read_tiles() if not t.loading]
    wrong = _wrong_tiles(shop, loaded)
    assert not wrong, "\n  ".join(["wrong tiles:", *wrong])


@then("the tiles are numbered without duplicates or gaps")
def tiles_numbered(shop: SwagLabs) -> None:
    numbers = [int(t.id.rsplit("-", 1)[-1]) for t in shop.lazy_catalogue().read_tiles()]
    assert numbers == list(range(len(numbers))), f"tile numbers {numbers}"


@when("I open the product slider")
def open_slider(shop: SwagLabs) -> None:
    shop.slider().open()


@then(parsers.parse("for {seconds:d} seconds the active dot always names the product on show"))
def dot_names_shown_product(shop: SwagLabs, memo: Memo, seconds: int) -> None:
    slider = shop.slider()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        shown, named = slider.snapshot()  # both read in ONE call: no torn read
        assert shown == named, f"slider shows {shown!r} but the active dot names {named!r}"
        if not memo.slider_seen or memo.slider_seen[-1] != shown:
            memo.slider_seen.append(shown)
        slider.pause(SAMPLE_EVERY_MS)


@then("the slider moved on by itself")
def slider_moved(memo: Memo) -> None:
    assert len(memo.slider_seen) >= 2, f"the slider never changed: {memo.slider_seen}"


@when(parsers.parse('I choose the slider dot for "{name}"'))
def choose_dot(shop: SwagLabs, name: str) -> None:
    slider = shop.slider()
    slider.start_recording()  # BEFORE the click: a change right after it cannot be missed
    slider.choose(name)


@then(parsers.parse('"{name}" is shown after my choice'))
def shown_after_choice(shop: SwagLabs, name: str) -> None:
    shop.eventually(shop.slider().history, lambda history: name in history, f"{name!r} should be shown")
