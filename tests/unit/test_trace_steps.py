"""Gherkin steps become groups in the Playwright trace (framework/plugins/trace_steps.py).

Run on a tiny pytest-bdd project in a sandbox, with a fake page that records the tracing calls:
no browser needed, and the real pytest-bdd hook order is exercised.
"""

import json

import pytest

pytest_plugins = ["pytester"]

FEATURE = """
Feature: Sandbox
  Scenario: Steps in the trace
    Given no browser yet
    And a browser
    When the user does something
    Then the check fails
"""

STEPS = """
import json
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from framework.plugins.trace_steps import remember_page

scenarios("features")
LOG = Path(__file__).with_name("tracing.json")
calls = []


class Tracing:
    def group(self, name):
        calls.append(f"group {name}")
        LOG.write_text(json.dumps(calls))

    def group_end(self):
        calls.append("end")
        LOG.write_text(json.dumps(calls))


class Context:
    tracing = Tracing()


class Page:
    context = Context()


@pytest.fixture
def page(request):
    page = Page()
    remember_page(request.node, page)
    return page


@given("no browser yet")
def no_browser():
    pass


@given("a browser")
def a_browser(page):
    pass


@when("the user does something")
def does_something(page):
    pass


@then("the check fails")
def check_fails(page):
    assert False, "the product is broken"
"""


def test_each_step_is_one_closed_group_even_when_it_fails(pytester: pytest.Pytester) -> None:
    pytester.makeini("[pytest]\naddopts = -p no:cacheprovider -p no:playwright\n")
    pytester.makeconftest('pytest_plugins = ["framework.plugins.trace_steps"]\n')
    (pytester.path / "features").mkdir()
    (pytester.path / "features" / "sandbox.feature").write_text(FEATURE, encoding="utf-8")
    (pytester.path / "test_sandbox.py").write_text(STEPS, encoding="utf-8")

    pytester.runpytest().assert_outcomes(failed=1)

    calls = json.loads((pytester.path / "tracing.json").read_text(encoding="utf-8"))
    assert calls == [
        # "Given no browser yet" has no page: nothing to group.
        "group And a browser",  # the step that creates the page is grouped too, keyword as written
        "end",
        "group When the user does something",
        "end",
        "group Then the check fails",
        "end",  # closed although the step failed
    ]
