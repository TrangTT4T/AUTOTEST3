"""One unique correlation id per flow (Day 10, Part 2.4): run, worker, test, and a short hash."""

from __future__ import annotations

import hashlib
import re


def correlation_id(run_uid: str, worker: str, nodeid: str, label: str = "") -> str:
    """``T-<run>-<worker>-<test slug>-<hash>[-label]``: readable in logs, unique across tests and runs."""
    name = nodeid.rsplit("::", 1)[-1]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40].rstrip("-")
    digest = hashlib.sha1(nodeid.encode("utf-8"), usedforsecurity=False).hexdigest()[
        :4
    ]  # a short id, not security
    suffix = f"-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}" if label else ""
    return f"T-{run_uid[:6]}-{worker}-{slug}-{digest}{suffix}"
