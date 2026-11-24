"""pytest plugin: browser fixtures, the ``shop`` fixture and failure evidence."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from swaglabs.app import PerfRecorder, SwagLabs
from swaglabs.config import Settings
from swaglabs.domain import Catalogue, reference_catalogue
from swaglabs.evidence import redact, slug
from swaglabs.network import BrowserMonitor

log = logging.getLogger("swaglabs.bdd")
PERF_PROPERTY = "perf"
SHOP_KEY = pytest.StashKey[SwagLabs]()


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    return Settings.from_pytest(pytestconfig)


@pytest.fixture(scope="session")
def catalogue() -> Catalogue:
    return reference_catalogue()


@pytest.fixture(scope="session", autouse=True)
def _expect_timeout(pytestconfig: pytest.Config) -> None:
    """``expect`` has its own 5 s default; align it with --ui-timeout like every action."""
    expect.set_options(timeout=int(pytestconfig.getoption("ui_timeout")))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Pin locale and time zone: identical formats and headers on every machine and in CI."""
    return {**browser_context_args, "locale": "en-US", "timezone_id": "UTC"}


@pytest.fixture
def shop(
    request: pytest.FixtureRequest, page: Page, settings: Settings, catalogue: Catalogue
) -> Iterator[SwagLabs]:
    """The application under test, in a FRESH browser context (pytest-playwright's ``page``).

    Fresh context = fresh cookies and localStorage: no test sees another test's session or cart,
    which is what makes ``-n auto`` safe.
    """
    page.set_default_timeout(settings.ui_timeout_ms)
    monitor = BrowserMonitor()
    monitor.attach(page.context)
    perf = PerfRecorder(monitor, test=request.node.nodeid)
    app = SwagLabs(page, settings, catalogue, monitor, perf)
    request.node.stash[SHOP_KEY] = app
    yield app
    # Measurements travel to the xdist controller inside the test report.
    request.node.user_properties.append((PERF_PROPERTY, [m.as_dict() for m in perf.measurements]))
    if monitor.blocked:
        log.info("blocked third-party requests: %s", dict(monitor.blocked))


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
    """Business-level evidence for the failed step (Playwright adds a trace and a screenshot)."""
    log.error("FAILED STEP: %s %s -> %s", step.keyword, step.name, type(exception).__name__)
    app = request.node.stash.get(SHOP_KEY, None)
    if app is None:  # the step failed before a browser existed
        return
    folder = Path(request.config.rootpath, "reports", "evidence", slug(request.node.name))
    folder.mkdir(parents=True, exist_ok=True)
    base = slug(f"{step.keyword}_{step.name}", limit=60)
    secrets = [app.settings.password]
    try:
        app.page.screenshot(path=folder / f"{base}.png", full_page=True)
        (folder / f"{base}.html").write_text(redact(app.page.content(), secrets), encoding="utf-8")
        url = app.page.url
    except Exception as error:  # noqa: BLE001 - the page may be gone (crash, closed context): keep what we have
        url = f"unavailable: {type(error).__name__}"
    record = {
        "scenario": scenario.name,
        "step": f"{step.keyword} {step.name}",
        "persona": app.settings.persona.value,
        "error": redact(str(exception), secrets)[:2000],
        "url": url,
        **app.monitor.as_dict(),
    }
    (folder / f"{base}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    log.error("evidence saved in %s", folder.relative_to(request.config.rootpath))
