"""Mobile end-to-end tests (Unit 3, Day 11): plain Appium tests on My Demo App.

They run only with ``--store mobile`` (the mobile plugin deselects them otherwise) and use
screen objects only (checked by the architecture tests).
"""

from __future__ import annotations

import pytest
from appium.webdriver.webdriver import WebDriver

from framework.adapters.mobile.forms import Address, Card
from framework.domain import Catalogue


@pytest.fixture
def app(mobile_app: WebDriver) -> WebDriver:
    """The app, freshly restarted, on its catalogue screen."""
    return mobile_app


@pytest.fixture
def catalogue(mobile_catalogue: Catalogue) -> Catalogue:
    return mobile_catalogue


@pytest.fixture
def shipping_address() -> Address:
    return Address("Test Customer", "1 Test Street", "Truro", "89750", "United Kingdom", state="Cornwall")


@pytest.fixture
def test_card() -> Card:
    # Not a real card; the app accepts it (its own Espresso test uses this number).
    return Card("Test Customer", "3258125675687891", "03/30", "123")
