"""pytest plugin: every Gherkin step becomes a named group in the Playwright trace.

Without it, the Trace Viewer of a failed scenario is one flat list of clicks and waits; with
it, the actions sit under "When they add the product to the cart", so the failing step is
found at a glance (Playwright's ``test.step``; Python has ``tracing.group`` instead).

The fixture that creates the browser page registers it with ``remember_page``. The group opens
in ``pytest_bdd_before_step_call`` - after the step's fixtures exist, so the step that starts
the browser is grouped too - and closes after the step, whether it passed or failed. With
tracing off, grouping is a no-op.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

PAGE_KEY = pytest.StashKey[Page]()
_OPEN_KEY = pytest.StashKey[Page]()


def remember_page(item: pytest.Item, page: Page) -> None:
    """Called by the fixture that owns the page, so steps can be grouped in its trace."""
    item.stash[PAGE_KEY] = page


def pytest_bdd_before_step_call(
    request: pytest.FixtureRequest,
    feature: Any,
    scenario: Any,
    step: Any,
    step_func: Any,
    step_func_args: Any,
) -> None:
    page = request.node.stash.get(PAGE_KEY, None)
    if page is None:  # a step without a browser (yet): nothing to group
        return
    page.context.tracing.group(f"{step.keyword} {step.name}")
    request.node.stash[_OPEN_KEY] = page


def _close_group(request: pytest.FixtureRequest) -> None:
    page = request.node.stash.get(_OPEN_KEY, None)
    if page is None:
        return
    del request.node.stash[_OPEN_KEY]
    with contextlib.suppress(PlaywrightError):  # the context is gone (crash): no trace to fix
        page.context.tracing.group_end()


def pytest_bdd_after_step(
    request: pytest.FixtureRequest,
    feature: Any,
    scenario: Any,
    step: Any,
    step_func: Any,
    step_func_args: Any,
) -> None:
    _close_group(request)


@pytest.hookimpl(trylast=True)  # after the evidence hooks: their screenshot belongs to the failed step
def pytest_bdd_step_error(
    request: pytest.FixtureRequest,
    feature: Any,
    scenario: Any,
    step: Any,
    step_func: Any,
    step_func_args: Any,
    exception: Exception,
) -> None:
    _close_group(request)
