"""Capability profiles for My Demo App.

Values that differ per machine (device, app path) come from options and
environment variables (framework/config.py); values that affect results are pinned.
"""

from __future__ import annotations

from typing import Any

from appium.options.android import UiAutomator2Options

from framework.config import Settings

APP_PACKAGE = "com.saucelabs.mydemoapp.android"
APP_ACTIVITY = ".view.activities.SplashActivity"  # launcher activity in AndroidManifest.xml


def android_options(settings: Settings) -> UiAutomator2Options:
    options = UiAutomator2Options()
    options.device_name = settings.android_device
    if settings.android_avd:
        options.avd = settings.android_avd  # Appium starts this emulator itself
    if settings.android_app:
        options.app = settings.android_app  # install this build
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.app_wait_activity = "*"  # the splash screen hands over to MainActivity
    options.auto_grant_permissions = True
    options.disable_window_animation = True  # fewer timing differences (Day 9, Part 5)
    options.language = "en"
    options.locale = "US"  # the app prices in USD; pin the device language as Unit 2 pinned en-GB
    options.new_command_timeout = 120
    options.no_reset = False
    return options


def android_capabilities(settings: Settings) -> dict[str, Any]:
    """The capabilities that will be sent — for reports and unit tests."""
    return dict(android_options(settings).to_capabilities())
