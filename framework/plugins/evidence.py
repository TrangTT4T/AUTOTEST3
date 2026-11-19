"""pytest plugin: step logging and business-level failure evidence."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pytest

from framework.adapters.web.store import WebStore

log = logging.getLogger("shop.bdd")


def _slug(text: str) -> str:
    return re.sub(r"\W+", "_", text).strip("_")[:120]


def pytest_bdd_before_scenario(request: pytest.FixtureRequest, feature: Any, scenario: Any) -> None:
    log.info("SCENARIO %s  tags=%s", scenario.name, sorted(scenario.tags))


def pytest_bdd_before_step(
    request: pytest.FixtureRequest, feature: Any, scenario: Any, step: Any, step_func: Any
) -> None:
    log.info("  %s %s", step.keyword, step.name)


def pytest_bdd_step_error(
    request: pytest.FixtureRequest,
    feature: Any,
    scenario: Any,
    step: Any,
    step_func: Any,
    step_func_args: dict[str, Any],
    exception: Exception,
) -> None:
    log.error("FAILED STEP: %s %s -> %r", step.keyword, step.name, exception)
    try:
        store = request.getfixturevalue("store")
    except Exception:  # noqa: BLE001 - the store itself failed to start (e.g. blocked): nothing to capture
        return
    if not isinstance(store, WebStore):
        return
    folder = Path(request.config.rootpath, "reports", "evidence", _slug(request.node.name))
    folder.mkdir(parents=True, exist_ok=True)
    base = _slug(f"{step.keyword}_{step.name}")
    store.page.screenshot(path=folder / f"{base}.png", full_page=True)
    (folder / f"{base}.json").write_text(
        json.dumps(
            {
                "scenario": scenario.name,
                "step": f"{step.keyword} {step.name}",
                "error": repr(exception),
                "url": store.page.url,
                **store.diagnostics.as_dict(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.error("evidence saved in %s", folder)
