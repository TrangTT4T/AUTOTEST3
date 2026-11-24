"""``eventually``: retry a read until the system has caught up (eventual consistency).

Playwright's ``expect`` already retries assertions on ONE element. Use ``eventually`` for
everything else: state that is not on screen (localStorage, cookies), values computed from
several elements, or "count grows to at least N" checks.

Two rules make it safe:
* it retries a READ (``probe``), never an action - retrying a click can do it twice;
* it fails with the LAST observed value, so the report says what the system did, not only
  that it timed out.

Pure logic: the clock and the sleep are injectable, so the unit tests run in microseconds.
In a browser test pass ``sleep=lambda s: page.wait_for_timeout(s * 1000)``: Playwright's sync
API only delivers browser events (requests, dialogs) while a Playwright call is running.
"""

from __future__ import annotations

import time
from collections.abc import Callable


def eventually[T](
    probe: Callable[[], T],
    predicate: Callable[[T], bool],
    *,
    timeout_s: float,
    description: str,
    interval_s: float = 0.1,
    backoff: float = 1.5,
    max_interval_s: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``probe`` until ``predicate(result)`` holds; return that result.

    Raises AssertionError (a test failure, not an error) with the last value on timeout.
    The wait between tries grows by ``backoff`` up to ``max_interval_s``: fast when the
    system is quick, gentle on it when it is slow.
    """
    if timeout_s <= 0 or interval_s <= 0 or backoff < 1:
        raise ValueError("timeout_s and interval_s must be positive and backoff >= 1")
    deadline = clock() + timeout_s
    wait = interval_s
    attempts = 0
    while True:
        value = probe()
        attempts += 1
        if predicate(value):
            return value
        remaining = deadline - clock()
        if remaining <= 0:
            raise AssertionError(
                f"{description}: not reached within {timeout_s:g} s ({attempts} tries); last value: {value!r}"
            )
        sleep(min(wait, remaining))
        wait = min(wait * backoff, max_interval_s)
