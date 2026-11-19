"""pytest plugin: Appium session, app reset, and mobile evidence.

Which tests run on which platform is decided in framework/plugins/selection.py.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
from appium.webdriver.webdriver import WebDriver

from framework.adapters.fake import MOBILE_SNAPSHOT
from framework.adapters.mobile import evidence
from framework.adapters.mobile.capabilities import android_capabilities
from framework.adapters.mobile.session import restart_app, start_android_session
from framework.config import Settings
from framework.domain import Catalogue
from framework.errors import EnvironmentBlockedError

log = logging.getLogger("shop.mobile")
REPORT_KEY = pytest.StashKey[dict[str, pytest.TestReport]]()
_SESSION_ERROR = pytest.StashKey[EnvironmentBlockedError]()


# ---------------------------------------------------------------------------- reports
@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    item.stash.setdefault(REPORT_KEY, {})[report.when] = report
    return report


def _failed(request: pytest.FixtureRequest) -> bool:
    reports = request.node.stash.get(REPORT_KEY, {})
    return any(r.failed for r in reports.values())


# ---------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def mobile_catalogue() -> Catalogue:
    """My Demo App's 24 products, extracted from its source (tools/extract_mobile_catalogue.py)."""
    return Catalogue.from_products_json(json.loads(MOBILE_SNAPSHOT.read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def mobile_driver(settings: Settings, pytestconfig: pytest.Config) -> Iterator[WebDriver]:
    """One Appium session per run (Day 9, 2.4); each test restarts the app for a known state.

    If the environment is not ready, every mobile test is reported BLOCKED with the reason,
    and the session start is not retried for each test.
    """
    if _SESSION_ERROR in pytestconfig.stash:
        raise pytestconfig.stash[_SESSION_ERROR]
    try:
        driver = start_android_session(settings)
    except EnvironmentBlockedError as error:
        pytestconfig.stash[_SESSION_ERROR] = error
        raise
    log.info("mobile session started: %s", evidence.safe_capabilities(dict(driver.capabilities)))
    driver.implicitly_wait(0)  # explicit waits only (Day 9, 5.2)
    yield driver
    driver.quit()


@pytest.fixture
def mobile_app(request: pytest.FixtureRequest, mobile_driver: WebDriver) -> Iterator[WebDriver]:
    """The app restarted for this test, recording on; evidence kept only if the test fails."""
    restart_app(mobile_driver)
    mobile_driver.start_recording_screen()
    yield mobile_driver
    folder = Path(request.config.rootpath, "reports", "mobile", re.sub(r"\W+", "_", request.node.name))
    if _failed(request):
        written = evidence.collect(mobile_driver, folder)
        evidence.save_recording(mobile_driver, folder / "recording.mp4")
        log.error("mobile evidence saved in %s: %s", folder, [p.name for p in written])
    else:
        try:
            mobile_driver.stop_recording_screen()  # discard
        except Exception as error:  # noqa: BLE001 - a failed discard must not fail a passing test
            log.warning("could not stop the recording: %r", error)


@pytest.fixture(scope="session")
def mobile_capabilities(settings: Settings) -> dict[str, object]:
    """What a mobile run asks Appium for — written into reports."""
    return android_capabilities(settings)
