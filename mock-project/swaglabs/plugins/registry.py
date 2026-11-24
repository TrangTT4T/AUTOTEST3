"""pytest plugin: load the registers, register markers, enforce tag rules and the coverage gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from swaglabs.config import add_options
from swaglabs.findings import Register, load_register
from swaglabs.requirements import Requirement, load_registry, tag_problems
from swaglabs.traceability import DeclaredScenario, declared_scenarios, requirement_index

REGISTRY_KEY = pytest.StashKey[dict[str, Requirement]]()
FINDINGS_KEY = pytest.StashKey[Register]()
SCENARIOS_KEY = pytest.StashKey[list[DeclaredScenario]]()

# Scenario-level tags with a meaning beyond "marker" (see pytest_bdd_apply_tag).
PHONE_CONTEXT = {"viewport": {"width": 412, "height": 915}, "has_touch": True}


def pytest_addoption(parser: pytest.Parser) -> None:
    add_options(parser)


def _path(config: pytest.Config, ini: str) -> Path:
    return Path(config.rootpath, str(config.getini(ini)))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    registry = load_registry(_path(config, "requirements_registry"))
    register = load_register(_path(config, "findings_register"), registry)
    config.stash[REGISTRY_KEY] = registry
    config.stash[FINDINGS_KEY] = register
    config.stash[SCENARIOS_KEY] = declared_scenarios(_path(config, "bdd_features_base_dir"))
    # Tags become markers; with --strict-markers every one must be registered.
    for req in registry.values():
        config.addinivalue_line("markers", f"{req.id}: {req.title} (risk {req.risk})")
    for area, meaning in register.areas.items():
        config.addinivalue_line("markers", f"area-{area}: {meaning}")
    config.addinivalue_line("markers", "phone: runs in a phone-sized touch-screen browser context")


def registry_of(config: pytest.Config) -> dict[str, Requirement]:
    return config.stash[REGISTRY_KEY]


def register_of(config: pytest.Config) -> Register:
    return config.stash[FINDINGS_KEY]


def scenarios_of(config: pytest.Config) -> list[DeclaredScenario]:
    return config.stash[SCENARIOS_KEY]


def pytest_bdd_apply_tag(tag: str, function: Any) -> bool | None:
    if tag == "manual":
        pytest.mark.manual(function)  # keeps -m "not manual" working
        pytest.mark.skip(reason="manual check - see docs/01-strategy.md")(function)
        return True
    if tag == "phone":
        pytest.mark.phone(function)
        pytest.mark.browser_context_args(**PHONE_CONTEXT)(function)
        return True
    return None  # default: the tag becomes a marker of the same name


def is_scenario(item: pytest.Item) -> bool:
    # pytest-bdd gives every scenario test this parameter. If a future version stops doing so,
    # the guard in pytest_collection_modifyitems fails the run instead of silently checking nothing.
    return "_pytest_bdd_example" in getattr(item, "fixturenames", ())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    scenarios = [item for item in items if is_scenario(item)]
    if any(item.path.name == "test_scenarios.py" for item in items) and not scenarios:
        raise pytest.UsageError(
            "Tag rules cannot find any BDD scenario; pytest-bdd may have changed how it marks "
            "scenarios (see swaglabs/plugins/registry.py)."
        )
    registry, areas = registry_of(config), register_of(config).areas
    problems = []
    for item in scenarios:
        tags = {marker.name for marker in item.iter_markers()}
        problems += [f"{item.name}: {p}" for p in tag_problems(tags, registry, areas)]
    if problems:
        raise pytest.UsageError("Tag rules broken:\n  " + "\n  ".join(problems))


def coverage_gaps(config: pytest.Config) -> list[str]:
    declared = scenarios_of(config)
    index = requirement_index(declared)
    gaps = [f"requirement {req} has no scenario" for req in registry_of(config) if req not in index]
    used_areas = {area for scenario in declared for area in scenario.areas}
    gaps += [
        f"finding {fid} has no scenario with its area, so a fix would never be noticed"
        for fid in register_of(config).untested(used_areas)
    ]
    return gaps


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """--fail-on-uncovered: every requirement and every finding needs a scenario."""
    config = session.config
    if not config.getoption("fail_on_uncovered") or hasattr(config, "workerinput"):
        return
    gaps = coverage_gaps(config)
    if gaps:
        writer = config.get_terminal_writer()
        for gap in gaps:
            writer.line(f"Coverage gate: {gap}", red=True)
        if session.exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
