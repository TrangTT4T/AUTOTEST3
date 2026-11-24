"""Architecture fitness tests: the layer rules from the README, checked on every run.

A rule that only lives in a document erodes; a rule that fails the build does not.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELECTOR_CALLS = {
    "locator",
    "get_by_role",
    "get_by_text",
    "get_by_label",
    "get_by_test_id",
    "get_by_placeholder",
}
# Files allowed to use locators outside pages/ and components/, with the reason.
SELECTOR_ALLOWLIST = {
    "framework/adapters/web/guard.py": "reads the whole <body> text to detect bot-check pages",
}


def _python_files(*folders: str) -> list[Path]:
    return sorted(p for folder in folders for p in (ROOT / folder).rglob("*.py"))


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@pytest.mark.parametrize("path", _python_files("tests/steps"), ids=_rel)
def test_steps_use_only_the_port_and_the_domain(path: Path) -> None:
    forbidden = {
        m for m in _imports(path) if m.startswith(("playwright", "appium", "selenium", "framework.adapters"))
    }
    assert not forbidden, f"{_rel(path)} imports {forbidden}: steps must talk to the Store port only"


@pytest.mark.parametrize(
    "path",
    [ROOT / "framework/domain.py", ROOT / "framework/ports.py", ROOT / "framework/errors.py"],
    ids=_rel,
)
def test_core_does_not_depend_on_tools(path: Path) -> None:
    forbidden = {m for m in _imports(path) if m.startswith(("playwright", "pytest", "pytest_bdd"))}
    assert not forbidden, f"{_rel(path)} imports {forbidden}: the core must stay tool-independent"


def test_selectors_live_only_in_pages_and_components() -> None:
    offenders: list[str] = []
    for path in _python_files("framework", "tests"):
        rel = _rel(path)
        if rel.startswith(("framework/adapters/web/pages/", "framework/adapters/web/components/")):
            continue
        if rel in SELECTOR_ALLOWLIST or rel.startswith("tests/unit/"):
            continue
        offenders.extend(
            f"{rel}:{node.lineno} .{node.attr}(...)"
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Attribute) and node.attr in SELECTOR_CALLS
        )
    assert not offenders, "selectors outside page objects:\n" + "\n".join(offenders)


# A bounded interval BETWEEN condition checks is the one legitimate sleep (Unit 3, Day 10).
SLEEP_ALLOWLIST = {
    "framework/waiting.py": "wait_until / holds_for: bounded interval between checks of a condition",
    "framework/perf/telemetry.py": "sampling period of a telemetry collector (a clock, not a wait)",
}


def test_no_sleep_anywhere() -> None:
    offenders = [
        f"{_rel(p)}:{n.lineno}"
        for p in _python_files("framework", "tests")
        if _rel(p) not in SLEEP_ALLOWLIST
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
        if isinstance(n, ast.Attribute) and n.attr in {"sleep", "wait_for_timeout"}
    ]
    assert not offenders, f"fixed waits found (wait for a condition instead): {offenders}"


def test_appium_lookups_live_only_in_screen_objects() -> None:
    offenders: list[str] = []
    for path in _python_files("framework", "tests"):
        rel = _rel(path)
        if rel.startswith(("framework/adapters/mobile/screens/", "tests/unit/")):
            continue
        offenders.extend(
            f"{rel}:{node.lineno} .{node.attr}(...)"
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Attribute) and node.attr in {"find_element", "find_elements"}
        )
    assert not offenders, "Appium lookups outside screen objects:\n" + "\n".join(offenders)


def test_the_sandbox_is_a_black_box() -> None:
    """framework/ and tests/ reach the order-events system over HTTP/WebSocket only, never by import."""
    offenders = [
        _rel(p)
        for p in _python_files("framework", "tests")
        if any(m == "sandbox" or m.startswith("sandbox.") for m in _imports(p))
    ]
    assert not offenders, f"importing the system under test: {offenders}"


@pytest.mark.parametrize("path", _python_files("tests/events", "tests/steps"), ids=_rel)
def test_events_tests_use_the_flow_not_the_wire(path: Path) -> None:
    forbidden = {m for m in _imports(path) if m.startswith(("urllib", "websockets", "aiohttp", "http"))}
    assert not forbidden, f"{_rel(path)} imports {forbidden}: talk to OrderFlow (framework/events)"


# Reads that return ONE snapshot of the page. Asserting on them directly races the UI: use the
# auto-retrying expect(...) (to_have_text / to_have_count / to_have_value / to_have_url ...).
SNAPSHOT_READS = frozenset(
    {
        "inner_text",
        "text_content",
        "input_value",
        "is_visible",
        "is_hidden",
        "is_enabled",
        "is_disabled",
        "is_checked",
        "is_editable",
        "all_inner_texts",
        "all_text_contents",
    }
)


def _snapshot_asserts(path: Path) -> list[int]:
    """Lines where an ``assert`` checks a one-off DOM read (zero-argument Locator reads, page.url)."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Assert):
            continue
        for sub in ast.walk(node.test):
            # Locator.count() takes no argument (list.count(x) does): only zero-argument reads count.
            snapshot = (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and not sub.args
                and sub.func.attr in SNAPSHOT_READS | {"count"}
            )
            page_url = (
                isinstance(sub, ast.Attribute)
                and sub.attr == "url"
                and isinstance(sub.value, ast.Attribute)
                and sub.value.attr == "page"
            )
            if snapshot or page_url:
                found.append(node.lineno)
    return sorted(set(found))


@pytest.mark.parametrize("path", _python_files("tests/pages", "tests/e2e"), ids=_rel)
def test_ui_checks_use_web_first_assertions(path: Path) -> None:
    lines = _snapshot_asserts(path)
    assert not lines, f"{_rel(path)}: assert on a one-off page read on lines {lines}; use expect(...)"


API_CLIENT_FILES = [ROOT / "framework/events/client.py", ROOT / "framework/adapters/web/api.py"]


@pytest.mark.parametrize("path", API_CLIENT_FILES, ids=_rel)
def test_api_clients_never_assert(path: Path) -> None:
    """A client calls the API and returns models; the TEST decides what is right (expect in the test).

    An AssertionError means "product defect" in this project and is what strict xfails accept, so a
    client raising one would turn a broken set-up call into an expected failure.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    found += [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Raise) and n.exc is not None and "AssertionError" in ast.unparse(n.exc)
    ]
    assert not found, f"{_rel(path)}: assertions on lines {found}; raise ApiRequestError instead"


def test_each_api_client_serves_one_domain() -> None:
    """One domain, one client: the transport lives in BaseClient only, endpoints in the domain clients."""
    from framework.events import client  # noqa: PLC0415 - imported where the rule is checked

    domain = {
        "orders": client.OrdersClient,
        "observe": client.ObservabilityClient,
        "admin": client.AdminClient,
    }
    prefixes = {
        "orders": ("/config", "/orders", "/ws"),
        "observe": ("/events", "/deliveries", "/payments", "/dlq"),
        "admin": ("/admin/",),
    }
    source = (ROOT / "framework/events/client.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for key, cls in domain.items():
        assert cls.__bases__ == (client.BaseClient,), f"{cls.__name__} must extend BaseClient directly"
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls.__name__)
        assert not any(
            isinstance(m, ast.FunctionDef) and m.name in {"_call", "_expect"} for m in node.body
        ), f"{cls.__name__} re-implements the transport"
        inside_fstrings = {id(v) for f in ast.walk(node) if isinstance(f, ast.JoinedStr) for v in f.values}
        paths = [
            ast.unparse(f)[2:] for f in ast.walk(node) if isinstance(f, ast.JoinedStr)
        ]  # f'/x/{y}' -> /x/{y}
        paths += [
            c.value
            for c in ast.walk(node)
            if isinstance(c, ast.Constant) and isinstance(c.value, str) and id(c) not in inside_fstrings
        ]
        paths = [p for p in paths if p.startswith("/")]
        stray = [p for p in paths if not p.startswith(prefixes[key])]
        assert not stray, f"{cls.__name__} calls endpoints of another domain: {stray}"


@pytest.mark.parametrize("path", _python_files("tests/events", "tests/steps"), ids=_rel)
def test_tests_receive_clients_from_fixtures(path: Path) -> None:
    """Tests never build a client (no `OrdersClient(url)` in a test): fixtures inject them."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    built = [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id.endswith(("Client", "SandboxApi"))
    ]
    assert not built, f"{_rel(path)}: builds a client on lines {built}; use the fixtures"


def _locator_violations(path: Path) -> list[str]:
    """Inline selectors in a page object or component: a get_by_* call, or .locator("literal")."""
    found = []
    label = _rel(path) if path.is_relative_to(ROOT) else path.name
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        name = node.func.attr
        literal = bool(node.args) and isinstance(node.args[0], ast.Constant | ast.JoinedStr)
        if name.startswith("get_by_") or (name == "locator" and literal):
            found.append(f"{label}:{node.lineno} .{name}(...)")
    return found


WEB_LOCATOR_FILES = _python_files("framework/adapters/web/pages", "framework/adapters/web/components")


@pytest.mark.parametrize("path", WEB_LOCATOR_FILES, ids=_rel)
def test_page_objects_declare_their_locators(path: Path) -> None:
    """Selectors are string constants in each class's Locators section; methods use the names."""
    offenders = _locator_violations(path)
    assert not offenders, "declare the selector as a constant in the Locators section:\n" + "\n".join(
        offenders
    )


def test_the_locator_rule_catches_inline_selectors(tmp_path: Path) -> None:
    sample = tmp_path / "page.py"
    sample.write_text(
        "class P:\n"
        "    def m(self):\n"
        "        self.page.get_by_role('button', name='Buy').click()\n"
        "        self.page.locator('#price')\n"
        "        self.page.locator(f'#row-{1}')\n"
        "        self.page.locator(self._price)\n"
        "    _price = '#price'\n",
        encoding="utf-8",
    )
    lines = [v.rsplit(":", 1)[1].split()[0] for v in _locator_violations(sample)]
    assert sorted(lines) == ["3", "4", "5"]  # ast.walk visits nodes breadth-first


MOBILE_LOCATOR_BUILDERS = {"Locator", "by_id", "by_accessibility_id", "by_xpath"}


@pytest.mark.parametrize("path", _python_files("framework/adapters/mobile/screens"), ids=_rel)
def test_screens_declare_their_locators(path: Path) -> None:
    """Mobile locators are built only in each screen class's Locators section, never inside a method."""
    offenders = []
    for function in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                literal = bool(node.args) and isinstance(node.args[0], ast.Constant | ast.JoinedStr)
                if name in MOBILE_LOCATOR_BUILDERS or (name in {"find_element", "find_elements"} and literal):
                    offenders.append(f"{_rel(path)}:{node.lineno} {name}(...) inside {function.name}()")
    assert not offenders, "declare it in the Locators section at the bottom of the class:\n" + "\n".join(
        offenders
    )


def test_page_defaults_are_set_in_one_place() -> None:
    """Timeouts are configured by framework/plugins/fixtures.py (configure_page, _expect_timeout) only."""
    calls = [
        f"{_rel(path)}:{node.lineno}"
        for path in _python_files("framework", "tests")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute)
        and node.attr in {"set_default_timeout", "set_default_navigation_timeout", "set_options"}
    ]
    assert [c.split(":")[0] for c in calls] == ["framework/plugins/fixtures.py"] * 2, calls


# Skip / xfail hygiene (Playwright's anti-patterns: a skip without a reason; a skip where a known
# bug should be tracked). Python has no ``test.fixme``: a known defect is a STRICT xfail limited to
# AssertionError, so it keeps running and goes red when the defect is fixed or the failure changes.
_SKIP_MARKS = {"pytest.mark.skip", "pytest.mark.skipif", "pytest.mark.xfail"}


def _skip_call_problems(call: ast.Call) -> list[str]:
    name = ast.unparse(call.func)
    keywords = {k.arg: k.value for k in call.keywords}
    if name == "pytest.xfail":
        return ["pytest.xfail() stops the test and never sees the fix"]
    if name == "pytest.skip":
        reason = call.args[0] if call.args else keywords.get("reason")
    elif name in _SKIP_MARKS:
        reason = keywords.get("reason")
    else:
        return []
    problems = []
    if reason is None or (isinstance(reason, ast.Constant) and not str(reason.value).strip()):
        problems.append(f"{name} without a reason")
    if name == "pytest.mark.xfail":
        strict = keywords.get("strict")
        if not (isinstance(strict, ast.Constant) and strict.value is True):
            problems.append("xfail must be strict=True (a fix must turn the run red)")
        if "raises" not in keywords:
            problems.append("xfail must name raises= (other failures must surface)")
    return problems


def _unexplained_skips(source: str) -> list[str]:
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            bare = [d for d in node.decorator_list if ast.unparse(d) in _SKIP_MARKS]
            problems += [f"line {d.lineno}: @{ast.unparse(d)} without a reason" for d in bare]
        elif isinstance(node, ast.Call):
            problems += [f"line {node.lineno}: {problem}" for problem in _skip_call_problems(node)]
    return problems


def test_the_skip_rule_catches_unexplained_skips() -> None:
    sample = (
        "import pytest\n"
        "@pytest.mark.skip\n"  # 2: bare
        "def a(): pytest.skip()\n"  # 3: no reason
        "@pytest.mark.skipif(True, reason='')\n"  # 4: empty reason
        "def b(): pytest.xfail('bug')\n"  # 5: imperative xfail
        "@pytest.mark.xfail(reason='bug #1')\n"  # 6: not strict, no raises
        "def c(): pytest.skip('no sold-out product right now')\n"  # fine
        "@pytest.mark.xfail(strict=True, raises=AssertionError, reason='bug #2')\n"  # fine
        "def d(): pass\n"
    )
    lines = sorted(int(p.split()[1].rstrip(":")) for p in _unexplained_skips(sample))
    assert lines == [2, 3, 4, 5, 6, 6]


def test_every_skip_and_xfail_says_why() -> None:
    problems = [
        f"{_rel(path)} {problem}"
        for path in _python_files("framework", "tests", "tools")
        for problem in _unexplained_skips(path.read_text(encoding="utf-8"))
    ]
    assert not problems, "\n".join(problems)
