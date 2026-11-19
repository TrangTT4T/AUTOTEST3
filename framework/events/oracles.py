"""Oracles for asynchronous flows (Day 10, Part 5.3). Pure functions, unit-tested."""

from __future__ import annotations

import itertools
from collections import Counter
from collections.abc import Sequence

from framework.events.model import Delivery

STATUS_ORDER = ("placed", "paid", "packed", "shipped")
_RANK = {status: rank for rank, status in enumerate(STATUS_ORDER)}


def backwards(statuses: Sequence[str]) -> list[str]:
    """Every step where the shown status went back to an earlier one, e.g. ['shipped -> packed']."""
    return [
        f"{before} -> {after}"
        for before, after in itertools.pairwise(statuses)
        if _RANK[after] < _RANK[before]
    ]


def repeated(statuses: Sequence[str]) -> list[str]:
    """Statuses shown more than once."""
    return sorted(status for status, n in Counter(statuses).items() if n > 1)


def redelivered(deliveries: Sequence[Delivery]) -> dict[str, int]:
    """Events delivered more than once to the same subscription: '<subscription> <type> <id>' -> count."""
    counts = Counter(f"{d.subscription} {d.type} {d.event_id}" for d in deliveries if d.result != "held")
    return {key: n for key, n in sorted(counts.items()) if n > 1}


def gaps(deliveries: Sequence[Delivery]) -> list[float]:
    """Seconds between consecutive deliveries (for backoff checks)."""
    return [round(b.at - a.at, 3) for a, b in itertools.pairwise(deliveries)]


def max_attempt(deliveries: Sequence[Delivery]) -> int:
    return max((d.delivery for d in deliveries), default=0)
