"""``memo``: what one scenario remembers between its steps (a new one per scenario)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

from swaglabs.app import SwagLabs
from swaglabs.domain import Product
from swaglabs.pages import SideMenu
from swaglabs.pages.inventory import Card


@dataclass
class Memo:
    cart_products: list[Product] = field(default_factory=list)  # what the scenario put in the cart
    card: Card | None = None  # the catalogue card a product page was opened from
    second_tab: SwagLabs | None = None
    menu: SideMenu | None = None
    slider_seen: list[str] = field(default_factory=list)


@pytest.fixture
def memo() -> Memo:
    return Memo()


def quoted(text: str) -> list[str]:
    """``'"A", "B" and "C"'`` -> ``['A', 'B', 'C']``: lists of names in one step."""
    return re.findall(r'"([^"]+)"', text)
