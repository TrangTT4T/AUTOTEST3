"""pytest plugin: register requirement markers and enforce tag rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from framework.requirements import Requirement, load_registry, tag_problems

REGISTRY_KEY = pytest.StashKey[dict[str, Requirement]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini("requirements_registry", "path to requirements.toml", default="requirements.toml")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    path = Path(config.rootpath, str(config.getini("requirements_registry")))
    registry = load_registry(path)
    config.stash[REGISTRY_KEY] = registry
    for req in registry.values():
        config.addinivalue_line("markers", f"{req.id}: {req.title} (risk {req.risk})")


def registry_of(config: pytest.Config) -> dict[str, Requirement]:
    return config.stash[REGISTRY_KEY]


def pytest_bdd_apply_tag(tag: str, function: Any) -> bool | None:
    if tag.startswith("defect-"):  # @defect-D-12-02 -> known_defect("D-12-02") (framework/plugins/events.py)
        pytest.mark.known_defect(tag.removeprefix("defect-"))(function)
        return True
    if tag == "manual":
        pytest.mark.manual(function)  # keep the marker so -m "not manual" works
        pytest.mark.skip(reason="Manual check - documented in the strategy")(function)
        return True
    return None


def _is_scenario(item: pytest.Item) -> bool:
    # pytest-bdd gives every scenario test this parameter. If a future version
    # stops doing so, the guard below fails the run loudly instead of letting
    # the tag rules silently check nothing.
    return "_pytest_bdd_example" in getattr(item, "fixturenames", ())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    registry = registry_of(config)
    problems = []
    scenarios = [item for item in items if _is_scenario(item)]
    # Feature files are bound by test_*.py modules directly in tests/; other test
    # folders (tests/unit, tests/pages) hold plain pytest tests.
    bound_modules = [item for item in items if item.path.parent.name == "tests"]
    if bound_modules and not scenarios:
        raise pytest.UsageError(
            "Tag rules cannot find any BDD scenario among the collected tests; "
            "pytest-bdd may have changed how it marks scenarios (see framework/plugins/tags.py)."
        )
    for item in scenarios:
        tags = {marker.name for marker in item.iter_markers()}
        problems += [f"{item.name}: {p}" for p in tag_problems(tags, registry)]
    if problems:
        raise pytest.UsageError("Tag rules broken:\n  " + "\n  ".join(problems))
