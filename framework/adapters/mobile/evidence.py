"""Mobile evidence on failure: screenshot, page source, device log, device and session facts."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from pathlib import Path
from typing import Any

from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

log = logging.getLogger("shop.mobile")
SECRET_KEYS = ("key", "token", "password", "secret", "access")


def safe_capabilities(capabilities: dict[str, Any]) -> dict[str, Any]:
    """Session capabilities for the report, with anything secret-looking masked."""
    return {
        k: ("***" if any(word in k.lower() for word in SECRET_KEYS) else v) for k, v in capabilities.items()
    }


def collect(driver: WebDriver, folder: Path, logcat_lines: int = 300) -> list[Path]:
    """Write everything that helps a diagnosis; one failing artefact never stops the others."""
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def save(name: str, produce: Any) -> None:
        try:
            content = produce()
            path = folder / name
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
            written.append(path)
        except Exception as error:  # noqa: BLE001 - evidence must never hide the original failure
            log.warning("could not collect %s: %r", name, error)

    save("screenshot.png", driver.get_screenshot_as_png)
    save("page_source.xml", lambda: driver.page_source)
    save(
        "logcat.txt",
        lambda: "\n".join(entry["message"] for entry in driver.get_log("logcat")[-logcat_lines:]),
    )
    save("device_info.json", lambda: json.dumps(driver.execute_script("mobile: deviceInfo"), indent=2))
    save("capabilities.json", lambda: json.dumps(safe_capabilities(dict(driver.capabilities)), indent=2))
    return written


def save_recording(driver: WebDriver, path: Path) -> Path | None:
    """Stop the screen recording and write it (Base64 video from Appium)."""
    try:
        data = driver.stop_recording_screen()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data))
    except (WebDriverException, binascii.Error, OSError) as error:  # a missing video never hides the failure
        log.warning("could not save the recording: %r", error)
        return None
    return path
