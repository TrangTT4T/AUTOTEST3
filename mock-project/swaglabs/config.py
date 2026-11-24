"""Run configuration: command-line option > environment variable > default.

Secrets never come from the command line (it ends up in shell history and CI logs): the
password is read from the environment only.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest

from swaglabs.personas import Persona

BASE_URL_ENV = "SWAGLABS_BASE_URL"
PASSWORD_ENV = "SWAGLABS_PASSWORD"  # noqa: S105 - the NAME of the variable, not a password
# Swag Labs prints this password on its own login page for everyone: it is public demo data,
# not a secret. It is still read from the environment first (so a private deployment can use a
# real secret) and masked in every log and report like a real one.
PUBLIC_DEMO_PASSWORD = "secret_sauce"  # noqa: S105 - public demo credential, see above


def add_options(parser: pytest.Parser) -> None:
    group = parser.getgroup("swaglabs", "Swag Labs mock project")
    group.addoption(
        "--persona",
        default=os.getenv("SWAGLABS_PERSONA", Persona.STANDARD.value),
        choices=[p.value for p in Persona.runnable()],
        help="demo account the suite runs as (env SWAGLABS_PERSONA)",
    )
    group.addoption(
        "--ui-timeout",
        type=int,
        default=int(os.getenv("SWAGLABS_UI_TIMEOUT_MS", "10000")),
        help="Playwright action/assertion timeout in milliseconds (env SWAGLABS_UI_TIMEOUT_MS)",
    )
    group.addoption(
        "--fail-on-uncovered",
        action="store_true",
        default=False,
        help="fail when a requirement has no scenario or a finding has no scenario that can detect it",
    )
    parser.addini("requirements_registry", "path to requirements.toml", default="requirements.toml")
    parser.addini("findings_register", "path to findings.toml", default="findings.toml")
    parser.addini("perf_budgets", "path to perf-budgets.toml", default="perf-budgets.toml")


def _ini(config: pytest.Config, name: str) -> str:
    """An ini value, or '' when no installed plugin declares that ini key."""
    try:
        return str(config.getini(name) or "")
    except ValueError:
        return ""


@dataclass(frozen=True)
class Settings:
    base_url: str
    persona: Persona
    ui_timeout_ms: int
    browser: str = "chromium"
    device: str = ""
    password: str = field(default=PUBLIC_DEMO_PASSWORD, repr=False)  # repr=False: never printed

    @classmethod
    def from_pytest(cls, config: pytest.Config, environ: Mapping[str, str] = os.environ) -> Settings:
        base_url = (
            config.getoption("base_url", default=None)
            or environ.get(BASE_URL_ENV)
            or _ini(config, "base_url")
        )
        if not base_url:
            raise pytest.UsageError(f"base_url is not set (--base-url, {BASE_URL_ENV} or pyproject.toml)")
        timeout = int(config.getoption("ui_timeout"))
        if timeout < 1000:
            raise pytest.UsageError(f"--ui-timeout is in milliseconds; {timeout} is too small to be meant")
        browsers = config.getoption("browser", default=None) or ["chromium"]
        return cls(
            base_url=str(base_url).rstrip("/"),
            persona=Persona.parse(str(config.getoption("persona"))),
            ui_timeout_ms=timeout,
            browser=str(browsers[0]),
            device=str(config.getoption("device", default=None) or ""),
            password=environ.get(PASSWORD_ENV) or PUBLIC_DEMO_PASSWORD,
        )

    @property
    def label(self) -> str:
        """Short run name for reports and artifacts: ``problem_user-chromium``."""
        target = self.device.replace(" ", "-") if self.device else self.browser
        return f"{self.persona.value}-{target}"

    def public(self) -> dict[str, Any]:
        """Everything safe to write into a report (no password)."""
        return {
            "base_url": self.base_url,
            "persona": self.persona.value,
            "browser": self.browser,
            "device": self.device or None,
            "ui_timeout_ms": self.ui_timeout_ms,
        }
