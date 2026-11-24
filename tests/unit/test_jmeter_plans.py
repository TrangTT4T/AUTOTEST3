"""Quality rules for the JMeter test plans (perf/*.jmx): policy as code for load tests.

A plan is code that sends traffic, so it is reviewed by tests, like the cloud configuration:
* bounded: every user count and duration comes from a property, and every loop has a limit;
* correct: every request is checked by an assertion (a fast error page is not a fast purchase);
* robust: timeouts are explicit, data files exist, results are written with -l (no GUI listeners);
* polite: a plan aimed at someone else's site has light defaults, think time, an identifying
  User-Agent, and a setUp guard that refuses heavier runs.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLANS = sorted((ROOT / "perf").glob("*.jmx"))
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
THIRD_PARTY_LIMITS = {"users": 10, "duration": 300}


def _tree(plan: Path) -> ET.Element:
    return ET.parse(plan).getroot()  # noqa: S314 - the project's own plans, not untrusted input


def _prop(element: ET.Element, name: str) -> str:
    for child in element:
        if child.get("name") == name:
            return child.text or ""
    return ""


def _children_of(root: ET.Element) -> list[tuple[ET.Element, ET.Element]]:
    """(element, its hashTree) pairs: in a .jmx file an element's children follow it in a sibling hashTree."""
    pairs = []
    for tree in root.iter("hashTree"):
        items = list(tree)
        pairs += [
            (items[i], items[i + 1]) for i in range(0, len(items) - 1, 2) if items[i + 1].tag == "hashTree"
        ]
    return pairs


def _default(expression: str) -> int:
    """The default of a property expression: ${__P(users,5)} -> 5."""
    match = re.fullmatch(r"\$\{__P\(\w+,(\d+)\)\}", expression)
    assert match, f"not a property with a numeric default: {expression!r}"
    return int(match.group(1))


def _domain(root: ET.Element) -> str:
    defaults = [e for e in root.iter("ConfigTestElement") if e.get("guiclass") == "HttpDefaultsGui"]
    assert len(defaults) == 1, "exactly one HTTP Request Defaults element"
    match = re.search(r"\$\{__P\(host,([^)]+)\)\}", _prop(defaults[0], "HTTPSampler.domain"))
    assert match, "the target host must come from the 'host' property, with a default"
    return match.group(1)


def test_there_are_plans() -> None:
    assert [p.name for p in PLANS] == [
        "blazedemo_purchase.jmx",
        "orders_sandbox.jmx",
        "orders_sandbox_profile.jmx",
    ]


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.name)
def test_plan_is_bounded_and_property_driven(plan: Path) -> None:
    root = _tree(plan)
    assert root.get("jmeter") == "5.6.3", "plans are verified with JMeter 5.6.3"
    groups = list(root.iter("ThreadGroup"))
    open_groups = list(root.iter("OpenModelThreadGroup"))
    assert groups or open_groups, "no thread group"
    for group in open_groups:
        schedule = _prop(group, "OpenModelThreadGroup.schedule")
        numbers = re.sub(r"\$\{__P\(\w+,[\d.]+\)\}", "", schedule)
        assert not re.search(r"\d", numbers.replace("rate(0/s)", "")), (
            f"{group.get('testname')}: every rate and duration in the schedule must be a property: {schedule}"
        )
        assert schedule.rstrip().endswith("rate(0/s)"), "the schedule must ramp down to zero"
    for group in groups:
        for name in ("ThreadGroup.num_threads", "ThreadGroup.ramp_time", "ThreadGroup.duration"):
            assert _prop(group, name).startswith("${__P("), (
                f"{group.get('testname')}: {name} must be a property"
            )
        assert _prop(group, "ThreadGroup.scheduler") == "true", "every run needs a duration"
    for loop in root.iter("WhileController"):
        assert "__P(max_" in _prop(loop, "WhileController.condition"), (
            f"unbounded loop {loop.get('testname')!r}"
        )


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.name)
def test_every_request_is_asserted(plan: Path) -> None:
    unchecked = [
        element.get("testname")
        for element, children in _children_of(_tree(plan))
        if element.tag == "HTTPSamplerProxy" and not any(c.tag.endswith("Assertion") for c in children)
    ]
    assert not unchecked, f"requests without an assertion: {unchecked}"


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.name)
def test_plan_is_robust(plan: Path) -> None:
    root = _tree(plan)
    assert not list(root.iter("ResultCollector")), "no GUI listeners: write results with -l"
    defaults = next(e for e in root.iter("ConfigTestElement") if e.get("guiclass") == "HttpDefaultsGui")
    for name in ("HTTPSampler.connect_timeout", "HTTPSampler.response_timeout"):
        assert _prop(defaults, name).isdigit(), f"{name} must be explicit"
    for data in root.iter("CSVDataSet"):
        assert (plan.parent / _prop(data, "filename")).is_file(), (
            f"missing data file {_prop(data, 'filename')}"
        )
    names = [t.get("testname") for t in root.iter("TransactionController")]
    assert len(names) == len(set(names)), f"duplicate transaction names: {names}"


@pytest.mark.parametrize(
    "plan", [p for p in PLANS if _domain(_tree(p)) not in LOCAL_HOSTS], ids=lambda p: p.name
)
def test_third_party_targets_get_polite_load(plan: Path) -> None:
    root = _tree(plan)
    group = next(root.iter("ThreadGroup"))
    assert _default(_prop(group, "ThreadGroup.num_threads")) <= THIRD_PARTY_LIMITS["users"]
    assert _default(_prop(group, "ThreadGroup.duration")) <= THIRD_PARTY_LIMITS["duration"]
    assert list(root.iter("UniformRandomTimer")) or list(root.iter("GaussianRandomTimer")), "think time"
    headers = [
        _prop(h, "Header.value") for h in root.iter("elementProp") if _prop(h, "Header.name") == "User-Agent"
    ]
    assert headers, "identify the test traffic with a User-Agent"
    assert not any(_prop(h, "HTTPSampler.image_parser") == "true" for h in root.iter("ConfigTestElement")), (
        "no embedded resources: they multiply the load on someone else's servers"
    )
    guard = [s for s in root.iter("JSR223Sampler") if "max_users" in _prop(s, "script")]
    assert guard, "a setUp guard must refuse runs above the agreed limits"
    assert list(root.iter("SetupThreadGroup")), "the guard runs in a setUp thread group, before any traffic"


def test_jtl_without_the_needed_columns_is_refused(tmp_path: Path) -> None:
    from framework.perf.jtl import read_jtl  # noqa: PLC0415 - kept next to the rule it tests

    path = tmp_path / "xml-or-trimmed.jtl"
    path.write_text("timeStamp,elapsed,label\n1,2,x\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"missing JTL columns \['responseCode', 'success', 'allThreads'\]"):
        read_jtl(path)


def test_load_profile_plan_matches_the_workload_model() -> None:
    """CT-PT 4.2.7: the script implements the load profile of the plan, not numbers of its own."""
    from framework.perf.model import jmeter_properties, load_workload  # noqa: PLC0415 - kept next to the rule

    plan = (ROOT / "perf" / "orders_sandbox_profile.jmx").read_text(encoding="utf-8")
    expected = jmeter_properties(load_workload(ROOT / "perf" / "workload.toml"))
    defaults = dict(re.findall(r"\$\{__P\((\w+),([\d.]+)\)\}", plan))
    assert {key: defaults.get(key) for key in expected} == expected


def test_load_profile_plan_prepares_validates_and_cleans_up() -> None:
    """CT-PT 4.2.6/4.2.8: init (validate, seed data), action, end (verify), and a stop rule."""
    root = _tree(ROOT / "perf" / "orders_sandbox_profile.jmx")
    setup = next(root.iter("SetupThreadGroup"))
    assert _prop(setup, "ThreadGroup.on_sample_error") == "stoptest", "an invalid environment stops the test"
    assert list(root.iter("PostThreadGroup")), "a tearDown group verifies the end state"
    listeners = [_prop(e, "script") for e in root.iter("JSR223Listener")]
    assert any("abort_error_pct" in script for script in listeners), (
        "an abort criterion watches the error rate"
    )
    names = [t.get("testname") for t in root.iter("TransactionController")]
    assert {"J1 Place order and track", "J1.1 Submit order", "J1.2 Wait until shipped"} <= set(names)
    think = [t for t in root.iter("TransactionController") if t.get("testname") == "J2 Check order status"]
    assert _prop(think[0], "TransactionController.includeTimers") == "false", (
        "think time is not response time"
    )
