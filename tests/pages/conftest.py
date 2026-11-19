"""Page-object tests: plain pytest-playwright tests against the live shop.

They prove every page object works and are the starting point for Unit 2.
They need a browser, so they are skipped in offline runs (``--store fake``).
"""

import pytest

from framework.config import Settings


@pytest.fixture(autouse=True)
def _live_only(settings: Settings) -> None:
    if settings.store != "web":
        pytest.skip("page-object tests need the live shop (run with --store web)")
