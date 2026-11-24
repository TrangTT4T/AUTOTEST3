"""pytest plugin: run as one persona - expected failures and persona-independent scenarios.

* A scenario whose @area-* tags match a finding for the persona under test becomes a STRICT
  expected failure that only an AssertionError satisfies (see findings.toml for the semantics).
* @persona-independent scenarios (they log in with their own explicit users) run in the
  standard_user job only; other jobs deselect them, so the matrix is not padded with repeats.
"""

from __future__ import annotations

import pytest

from swaglabs.personas import Persona
from swaglabs.plugins.registry import is_scenario, register_of
from swaglabs.requirements import area_tags


@pytest.hookimpl(trylast=True)  # after the tag rules have accepted the scenarios
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    persona = Persona.parse(str(config.getoption("persona")))
    register = register_of(config)
    keep, drop = [], []
    for item in items:
        if not is_scenario(item):
            keep.append(item)
            continue
        names = {marker.name for marker in item.iter_markers()}
        if "persona-independent" in names and persona is not Persona.STANDARD:
            drop.append(item)
            continue
        keep.append(item)
        expected = register.expected_failures(persona, area_tags(names))
        if expected:
            reason = "; ".join(f"{f.id} {f.title}" for f in expected)
            item.add_marker(pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason))
            for finding in expected:
                item.add_marker(pytest.mark.known_defect(finding.id))
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
