from typing import Any

import pytest

from swaglabs.config import BASE_URL_ENV, PASSWORD_ENV, PUBLIC_DEMO_PASSWORD, Settings
from swaglabs.personas import Persona


class FakeConfig:
    """The two pytest.Config methods Settings uses."""

    def __init__(self, **options: Any) -> None:
        self.options = {
            "base_url": "https://shop.example/",
            "persona": "problem_user",
            "ui_timeout": 8000,
            "browser": ["firefox"],
            "device": None,
            **options,
        }

    def getoption(self, name: str, default: Any = None) -> Any:
        return self.options.get(name, default)

    def getini(self, name: str) -> Any:
        return "https://ini.example" if name == "base_url" else ""


def make(environ: dict[str, str] | None = None, **options: Any) -> Settings:
    return Settings.from_pytest(FakeConfig(**options), environ or {})  # type: ignore[arg-type]


def test_options_become_settings() -> None:
    settings = make()
    assert settings.base_url == "https://shop.example"
    assert settings.persona is Persona.PROBLEM
    assert settings.label == "problem_user-firefox"
    assert make(device="Pixel 7").label == "problem_user-Pixel-7"


def test_password_comes_from_the_environment_and_is_never_shown() -> None:
    settings = make({PASSWORD_ENV: "from-env"})
    assert settings.password == "from-env"
    assert "from-env" not in repr(settings)
    assert "password" not in settings.public()
    assert make().password == PUBLIC_DEMO_PASSWORD


def test_base_url_precedence_option_then_environment_then_ini() -> None:
    assert make({BASE_URL_ENV: "https://env.example"}).base_url == "https://shop.example"
    assert make({BASE_URL_ENV: "https://env.example"}, base_url=None).base_url == "https://env.example"
    assert make(base_url=None).base_url == "https://ini.example"


def test_missing_base_url_is_a_usage_error() -> None:
    class NoIni(FakeConfig):
        def getini(self, name: str) -> Any:
            raise ValueError(name)

    with pytest.raises(pytest.UsageError, match="base_url is not set"):
        Settings.from_pytest(NoIni(base_url=None), {})  # type: ignore[arg-type]


def test_refuses_a_timeout_given_in_seconds() -> None:
    with pytest.raises(pytest.UsageError, match="milliseconds"):
        make(ui_timeout=10)
