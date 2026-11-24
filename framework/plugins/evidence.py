"""pytest plugin: step logging and business-level failure evidence.

Global setup, once per run: the controller removes what an EARLIER pytest run left in reports/
(see ``RUN_OUTPUTS``) before any xdist worker starts, so evidence folders, logs and traces always
belong to this run. Outputs of other tools (perf/, coverage.xml, audit.md, ...) are not touched.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from framework.adapters.web.store import WebStore

log = logging.getLogger("shop.bdd")

# What pytest writes under reports/ (``artifacts`` is pytest-playwright's --output).
RUN_OUTPUTS = ("evidence", "events", "mobile", "artifacts", "traceability.csv", "traceability.md")


def reset_run_outputs(reports: Path) -> list[str]:
    """Delete this suite's outputs of an earlier run. Idempotent; returns what was removed."""
    removed = []
    for name in RUN_OUTPUTS:
        path = reports / name
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        else:
            continue
        removed.append(name)
    return removed


def pytest_configure(config: pytest.Config) -> None:
    # The controller configures before any worker exists; a worker must never do this, or it would
    # delete what faster workers have already written.
    if hasattr(config, "workerinput") or config.option.collectonly:
        return
    reset_run_outputs(Path(config.rootpath, "reports"))


@pytest.fixture(scope="session")
def delete_output_dir() -> None:
    """Replaces pytest-playwright's clean-up of ``--output`` (reports/artifacts) with nothing.

    Theirs is a session fixture, i.e. it runs once PER xdist WORKER, at that worker's first test: a
    late worker can delete traces that a faster worker has already saved. ``pytest_configure``
    above cleans reports/artifacts once, before any worker starts.
    """


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
