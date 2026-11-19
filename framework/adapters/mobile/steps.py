"""``mobile_step``: the mobile counterpart of ``business_step`` — names a part of a test in the log.

Appium has no trace groups; the log, the recording, and the per-test evidence folder
carry the story instead.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

log = logging.getLogger("shop.mobile")


@contextmanager
def mobile_step(title: str) -> Iterator[None]:
    log.info("STEP %s", title)
    yield
