"""Appium session lifecycle: start, classify environment failures, reset the app."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from appium import webdriver
from appium.webdriver.webdriver import WebDriver

from framework.adapters.mobile.capabilities import APP_PACKAGE, android_options
from framework.config import Settings
from framework.errors import EnvironmentBlockedError

# Messages that mean "the mobile environment is not ready", not "the app is broken".
_ENVIRONMENT_PROBLEMS = re.compile(
    r"ANDROID_HOME|ANDROID_SDK_ROOT|Could not find a connected Android device|"
    r"no (connected )?devices?|adb.*not found|emulator.*(not found|did not start)|"
    r"Could not find a driver for automationName|Connection refused|Max retries exceeded",
    re.IGNORECASE,
)


def is_environment_problem(message: str) -> bool:
    """True if a session error describes the environment (SDK, device, server), not the app."""
    return bool(_ENVIRONMENT_PROBLEMS.search(message))


def server_status(appium_url: str, timeout: float = 5.0) -> dict[str, object]:
    """GET /status. Raises EnvironmentBlockedError if no Appium server answers."""
    if urllib.parse.urlparse(appium_url).scheme not in {"http", "https"}:
        raise ValueError(f"--appium-url must be an http(s) URL, got {appium_url!r}")
    try:
        with urllib.request.urlopen(f"{appium_url}/status", timeout=timeout) as response:  # noqa: S310 - checked above
            return dict(json.load(response).get("value", {}))
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise EnvironmentBlockedError(f"no Appium server at {appium_url}: {error}") from error


def start_android_session(settings: Settings) -> WebDriver:
    server_status(settings.appium_url)
    try:
        return webdriver.Remote(settings.appium_url, options=android_options(settings))
    except Exception as error:  # Selenium/Appium wrap many causes in WebDriverException
        first_line = str(error).strip().splitlines()[0] if str(error).strip() else repr(error)
        if is_environment_problem(str(error)):
            raise EnvironmentBlockedError(f"mobile environment not ready: {first_line}") from error
        raise


def restart_app(driver: WebDriver) -> None:
    """Known state for the next test: the app keeps cart and login in memory, so a
    process restart clears them (from the source; confirm on a device)."""
    driver.terminate_app(APP_PACKAGE)
    driver.activate_app(APP_PACKAGE)
