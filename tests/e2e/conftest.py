"""End-to-end workflow tests (Unit 2, Day 7): plain Playwright tests on the live shop.

Every test here:
* is skipped offline (``--store fake``): they need the real shop;
* runs with third-party telemetry answered by an empty 204 (see network.py), so it
  depends only on the shop itself;
* uses page objects through ``shop``; no raw selectors (checked by architecture tests).
"""

from __future__ import annotations

from collections import Counter

import pytest
from playwright.sync_api import BrowserContext

from framework.adapters.web.network import silence_third_parties
from framework.config import Settings


@pytest.fixture(autouse=True)
def _live_only(settings: Settings) -> None:
    if settings.store != "web":
        pytest.skip("end-to-end tests need the live shop (run with --store web)")


@pytest.fixture(autouse=True)
def silenced(_live_only: None, context: BrowserContext) -> Counter[str]:
    """Third-party requests answered with 204 in this test's context, counted per host."""
    return silence_third_parties(context)
