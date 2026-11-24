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
ALLOWED_FIXED_WAITS = {"swaglabs/waiting.py", "swaglabs/app.py", "swaglabs/pages/dynamic.py"}


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
