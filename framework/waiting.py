"""Waiting for conditions, never for time (Unit 3, Day 10, Part 3).

Shared by the mobile screens and the asynchronous-system tests. This module holds the
only ``time.sleep`` in the framework: a short, bounded interval between checks.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(
    read: Callable[[], T],
    done: Callable[[T], bool],
    *,
    timeout: float = 10.0,
    interval: float = 0.1,
    backoff: float = 2.0,
    max_interval: float = 2.0,
) -> T:
    """Poll ``read()`` until ``done(value)`` holds; return it, or raise with the last value (Day 10)."""
    deadline = time.monotonic() + timeout
    value = read()
    while not done(value):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"condition not met within {timeout}s; last value: {value!r}")
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))  # bounded poll interval
        interval = min(interval * backoff, max_interval)
        value = read()
    return value


def holds_for(
    read: Callable[[], T],
    condition: Callable[[T], bool],
    *,
    duration: float,
    interval: float = 0.05,
) -> T:
    """Check that ``condition(read())`` stays true for ``duration`` seconds (an invariant over a window).

    Fails at the first violation, with the value and the moment. Use it for "nothing more
    happens": no second charge after a late answer, no progress while a worker is down.
    """
    started = time.monotonic()
    deadline = started + duration
    value = read()
    while True:
        if not condition(value):
            raise AssertionError(f"condition broken after {time.monotonic() - started:.2f}s: {value!r}")
        if time.monotonic() >= deadline:
            return value
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))  # bounded poll interval
        value = read()


def wait_until_stable(
    read: Callable[[], T],
    *,
    quiet: float,
    timeout: float,
    interval: float = 0.05,
) -> T:
    """Return ``read()`` once it has stopped changing for ``quiet`` seconds (the system went quiet).

    "Exactly once" can only be judged after the last redelivery or late answer could have
    happened; checking earlier passes before the fault has even played out.
    """
    deadline = time.monotonic() + timeout
    value = read()
    unchanged_since = time.monotonic()
    while time.monotonic() - unchanged_since < quiet:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"still changing after {timeout}s; last value: {value!r}")
        time.sleep(interval)  # bounded poll interval
        new = read()
        if new != value:
            value, unchanged_since = new, time.monotonic()
    return value
