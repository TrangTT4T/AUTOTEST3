"""Rules about the code itself, checked on every run: they stop the slow decay of a framework."""

import ast
from pathlib import Path

import pytest

from swaglabs.config import PUBLIC_DEMO_PASSWORD

ROOT = Path(__file__).resolve().parents[2]
PAGES = sorted((ROOT / "swaglabs" / "pages").glob("*.py"))
STEPS = sorted((ROOT / "tests" / "steps").glob("*.py"))
LOCATORS_MARKER = "# --- Locators ---"


def _classes(path: Path) -> list[ast.ClassDef]:
    return [n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.ClassDef)]


def _selector_constants(cls: ast.ClassDef) -> list[ast.Assign]:
    return [
        node
        for node in cls.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and all(isinstance(t, ast.Name) and t.id.startswith("_") for t in node.targets)
    ]


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_locators_are_declared_at_the_bottom_of_each_page_class(path: Path) -> None:
    source = path.read_text(encoding="utf-8").splitlines()
    for cls in _classes(path):
        constants = _selector_constants(cls)
        if not constants:
            continue
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        last_method_end = max((m.end_lineno or m.lineno for m in methods), default=cls.lineno)
        misplaced = [c.lineno for c in constants if c.lineno < last_method_end]
        assert misplaced == [], f"{path.name}:{cls.name}: selectors above a method on lines {misplaced}"
        first = min(c.lineno for c in constants)
        section = "\n".join(source[last_method_end : first - 1])
        assert LOCATORS_MARKER in section, f"{path.name}:{cls.name}: put '{LOCATORS_MARKER}' above them"


@pytest.mark.parametrize("path", [p for p in PAGES if p.name != "__init__.py"], ids=lambda p: p.name)
def test_each_page_file_holds_one_class_and_no_module_level_selectors(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1, f"{path.name}: {classes} - one page object per file"
    loose = [
        n.lineno
        for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
    ]
    assert loose == [], (
        f"{path.name}: module-level strings on lines {loose}; declare them at the bottom of the class"
    )


@pytest.mark.parametrize("path", PAGES, ids=lambda p: p.name)
def test_page_methods_use_declared_selectors_not_literals(path: Path) -> None:
    offenders = []
    for cls in _classes(path):
        for method in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            for call in (n for n in ast.walk(method) if isinstance(n, ast.Call)):
                name = call.func.attr if isinstance(call.func, ast.Attribute) else ""
                first = call.args[0] if call.args else None
                literal = isinstance(first, ast.Constant) and isinstance(first.value, str)
                if name in {"find", "locator"} and literal:
                    offenders.append(f"{cls.name}.{method.name}:{call.lineno}")
    assert offenders == [], f"{path.name}: inline selectors in {offenders}"


@pytest.mark.parametrize("path", STEPS, ids=lambda p: p.name)
def test_steps_never_touch_playwright(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = [
        n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import | ast.ImportFrom)
    ]
    playwright = [m for m in imports if m and m.startswith("playwright")]
    assert playwright == [], "steps talk to SwagLabs, not to Playwright"
    page_access = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "page"]
    assert page_access == [], f"{path.name}: '.page' used on lines {page_access}; add a SwagLabs method"


# The retry helper itself (it documents the rule), its browser adapter, and the slider's sampling cadence.


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


@pytest.mark.parametrize("path", STEPS, ids=lambda p: p.name)
def test_steps_check_the_ui_with_web_first_assertions(path: Path) -> None:
    lines = _snapshot_asserts(path)
    assert not lines, (
        f"{path.name}: assert on a one-off page read on lines {lines}; add a page-object expect_*"
    )


ALLOWED_FIXED_WAITS = {"swaglabs/waiting.py", "swaglabs/app.py", "swaglabs/pages/slider_catalog.py"}


def test_no_fixed_sleeps() -> None:
    offenders = []
    for path in [*sorted((ROOT / "swaglabs").rglob("*.py")), *sorted((ROOT / "tests").rglob("*.py"))]:
        rel = path.relative_to(ROOT).as_posix()
        if rel == "tests/unit/test_architecture.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "time.sleep(" in text and rel != "swaglabs/waiting.py":
            offenders.append(f"{rel}: time.sleep")
        if "wait_for_timeout(" in text and rel not in ALLOWED_FIXED_WAITS:
            offenders.append(f"{rel}: wait_for_timeout")
    assert offenders == [], "wait for a state (expect / eventually), not for time: " + ", ".join(offenders)


def test_no_password_in_feature_files_or_docs() -> None:
    texts = [*(ROOT / "features").rglob("*.feature"), *(ROOT / "docs").rglob("*.md")]
    leaks = [p.name for p in texts if PUBLIC_DEMO_PASSWORD in p.read_text(encoding="utf-8")]
    assert leaks == [], "feature files say (valid); docs say 'the password shown on the login page'"


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
        f"{path.relative_to(ROOT).as_posix()} {problem}"
        for folder in ("swaglabs", "tests")
        for path in sorted((ROOT / folder).rglob("*.py"))
        for problem in _unexplained_skips(path.read_text(encoding="utf-8"))
    ]
    assert not problems, "\n".join(problems)
