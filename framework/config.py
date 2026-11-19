"""Run configuration: command-line option > environment variable > default."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, cast

import pytest

StoreKind = Literal["web", "fake", "mobile"]


def add_options(parser: pytest.Parser) -> None:
    group = parser.getgroup("shop", "Shop test framework")
    group.addoption(
        "--store",
        choices=["web", "fake", "mobile"],
        default=os.getenv("SHOP_STORE", "web"),
        help="web = live shop in a browser; fake = in-memory, offline; mobile = My Demo App via Appium "
        "(env SHOP_STORE)",
    )
    group.addoption(
        "--appium-url",
        default=os.getenv("SHOP_APPIUM_URL", "http://127.0.0.1:4723"),
        help="Appium server URL (env SHOP_APPIUM_URL)",
    )
    group.addoption(
        "--android-app",
        default=os.getenv("SHOP_ANDROID_APP", ""),
        help="path or URL of the My Demo App .apk (env SHOP_ANDROID_APP)",
    )
    group.addoption(
        "--android-device",
        default=os.getenv("SHOP_ANDROID_DEVICE", "Android Emulator"),
        help="device name, or the emulator's AVD name with --android-avd (env SHOP_ANDROID_DEVICE)",
    )
    group.addoption(
        "--android-avd",
        default=os.getenv("SHOP_ANDROID_AVD", ""),
        help="AVD name for Appium to start the emulator itself (env SHOP_ANDROID_AVD)",
    )
    group.addoption(
        "--sandbox-url",
        default=os.getenv("SHOP_SANDBOX_URL", ""),
        help="use this running order-events sandbox instead of starting one per worker "
        "(env SHOP_SANDBOX_URL)",
    )
    group.addoption(
        "--sandbox-build",
        choices=["release", "fixed"],
        default=os.getenv("SHOP_SANDBOX_BUILD", "release"),
        help="order-events sandbox build under test; decides which known defects are expected "
        "(env SHOP_SANDBOX_BUILD)",
    )
    group.addoption(
        "--ui-timeout",
        type=int,
        default=int(os.getenv("SHOP_UI_TIMEOUT_MS", "15000")),
        help="Playwright default timeout in milliseconds (env SHOP_UI_TIMEOUT_MS)",
    )
    group.addoption(
        "--fail-on-uncovered",
        action="store_true",
        default=False,
        help="fail the run if any registered requirement has no scenario",
    )


@dataclass(frozen=True)
class Settings:
    base_url: str
    store: StoreKind
    ui_timeout_ms: int
    fail_on_uncovered: bool
    appium_url: str = "http://127.0.0.1:4723"
    android_app: str = ""
    android_device: str = "Android Emulator"
    android_avd: str = ""
    sandbox_url: str = ""
    sandbox_build: str = "release"

    @classmethod
    def from_pytest(cls, config: pytest.Config) -> Settings:
        base_url = config.getoption("base_url", default=None) or config.getini("base_url")
        if not base_url:
            raise pytest.UsageError("base_url is not set (pyproject.toml or --base-url)")
        return cls(
            base_url=str(base_url).rstrip("/"),
            store=cast(StoreKind, config.getoption("store")),
            ui_timeout_ms=int(config.getoption("ui_timeout")),
            fail_on_uncovered=bool(config.getoption("fail_on_uncovered")),
            appium_url=str(config.getoption("appium_url")).rstrip("/"),
            android_app=str(config.getoption("android_app")),
            android_device=str(config.getoption("android_device")),
            android_avd=str(config.getoption("android_avd")),
            sandbox_url=str(config.getoption("sandbox_url")).rstrip("/"),
            sandbox_build=str(config.getoption("sandbox_build")),
        )
