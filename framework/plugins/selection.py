"""pytest plugin: platform selection — which tests a run executes; the others are deselected.

| --store | BDD @web | BDD @mobile | BDD @events | tests/e2e, tests/pages | tests/mobile | tests/events |
|---|---|---|---|---|---|---|
| fake   | run (web catalogue) | run (app catalogue) | run | — | — | run |
| web    | run | — | — | run | — | — |
| mobile | — | run | — | — | run | — |

``--store fake`` is "everything that runs locally": in-memory stores and the local
order-events sandbox. Unit tests run in every mode.
"""

from __future__ import annotations

import pytest

_DESELECTED = pytest.StashKey[dict[str, int]]()
PLATFORMS = {"web", "mobile", "api", "events"}


def _platforms(item: pytest.Item) -> set[str]:
    return {m.name for m in item.iter_markers() if m.name in PLATFORMS}


FOLDER_STORES = {
    "mobile": ("mobile", "mobile tests need --store mobile"),
    "e2e": ("web", "web tests need --store web"),
    "pages": ("web", "web tests need --store web"),
    "events": ("fake", "events tests run with --store fake (local sandbox)"),
}


def deselect_reason(store: str, folder: str, platforms: set[str]) -> str | None:
    """Why a test does not belong to this run, or None. Pure: unit-tested."""
    if folder in FOLDER_STORES:
        needed, reason = FOLDER_STORES[folder]
        return None if store == needed else reason
    if folder == "tests" and platforms:  # a BDD scenario
        if "events" in platforms:
            return None if store == "fake" else "events scenarios run with --store fake (local sandbox)"
        if store == "web" and "web" not in platforms:
            return "scenario not tagged @web"
        if store == "mobile" and "mobile" not in platforms:
            return "scenario not tagged @mobile"
    return None


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect (not skip) what this platform cannot run.

    Skipped tests would be counted as "manual" in the traceability matrix; deselected
    ones are simply not part of this run (status NOT RUN), and a summary line says why.
    """
    store = str(config.getoption("store"))
    kept, removed = [], []
    reasons: dict[str, int] = {}
    for item in items:
        reason = deselect_reason(store, item.path.parent.name, _platforms(item))
        if reason is None:
            kept.append(item)
        else:
            removed.append(item)
            reasons[reason] = reasons.get(reason, 0) + 1
    if removed:
        config.hook.pytest_deselected(items=removed)
        items[:] = kept
    config.stash[_DESELECTED] = reasons


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, config: pytest.Config) -> None:
    reasons = config.stash.get(_DESELECTED, {})
    if reasons:
        summary = ", ".join(f"{n} ({reason})" for reason, n in sorted(reasons.items()))
        terminalreporter.write_line(
            f"Platform selection (--store {config.getoption('store')}): deselected {summary}"
        )
