"""Static review of the BDD layer: step usage, duplication, and Gherkin smells.

Run from the project root:

    python -m framework.review            # print the report, write reports/bdd-review.md
    python -m framework.review --strict   # also exit 1 if any problem is found (for CI)

Everything here is static: no browser, no pytest session. The functions are
pure so they can be unit-tested (tests/unit/test_review.py).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import parse
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from framework.requirements import load_registry
from framework.step_types import STEP_TYPES
from framework.traceability import declared_scenarios

KEYWORD_OF_TYPE = {"Context": "given", "Action": "when", "Outcome": "then"}
MAX_STEPS = 7
NEAR_DUPLICATE_RATIO = 0.85
# Words that describe the user interface instead of behaviour (Day 1, section 3.4).
IMPERATIVE = re.compile(
    r"\b(click|clicks|press|presses|tap|taps|type|types|button|textbox|dropdown|checkbox|"
    r"css|xpath|selector|url|https?)\b|#\w+",
    re.IGNORECASE,
)
HARD_CODED_MONEY = re.compile(r"[£$€]\s?\d")
# A quoted placeholder without a type, e.g. "{name}", also matches text containing quotes.
GREEDY_PLACEHOLDER = re.compile(r'"\{\w+\}"')


# --------------------------------------------------------------------------- model
@dataclass(frozen=True)
class StepDef:
    keyword: str  # given / when / then
    pattern: str
    kind: str  # exact / parse / re
    function: str
    location: str

    def matches(self, text: str) -> bool:
        if self.kind == "exact":
            return text == self.pattern
        if self.kind == "parse":
            return parse.parse(self.pattern, text, extra_types=STEP_TYPES) is not None
        return re.fullmatch(self.pattern, text) is not None


@dataclass(frozen=True)
class StepUse:
    keyword: str
    text: str
    location: str


@dataclass(frozen=True)
class ScenarioInfo:
    name: str
    location: str
    steps: tuple[StepUse, ...]
    examples: int  # rows for an outline, 1 for a plain scenario
    tags: frozenset[str] = frozenset()

    @property
    def manual(self) -> bool:
        return "manual" in self.tags


@dataclass
class Review:
    definitions: list[StepDef]
    scenarios: list[ScenarioInfo]
    usage: Counter[StepDef] = field(default_factory=Counter)
    undefined: list[StepUse] = field(default_factory=list)
    manual_steps: list[StepUse] = field(default_factory=list)  # in @manual scenarios: not automated
    ambiguous: list[tuple[StepUse, list[StepDef]]] = field(default_factory=list)
    near_duplicates: list[tuple[StepDef, StepDef, float]] = field(default_factory=list)
    smells: list[tuple[str, str, str]] = field(default_factory=list)  # (rule, where, detail)
    uncovered_requirements: list[str] = field(default_factory=list)

    @property
    def unused(self) -> list[StepDef]:
        return [d for d in self.definitions if self.usage[d] == 0]

    @property
    def problem_count(self) -> int:
        """Problems that fail ``--strict``. Near-duplicates are only candidates for a human to judge."""
        return (
            len(self.undefined)
            + len(self.ambiguous)
            + len(self.unused)
            + len(self.smells)
            + len(self.uncovered_requirements)
        )


# ---------------------------------------------------------------- step definitions
def _step_keyword(decorator: ast.expr) -> str | None:
    func = decorator.func if isinstance(decorator, ast.Call) else None
    name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
    return name if name in {"given", "when", "then"} else None


def _pattern(arg: ast.expr) -> tuple[str, str] | None:
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value, "exact"
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Name)
        and arg.func.id == "parsed"
        and arg.args
        and isinstance(arg.args[0], ast.Constant)
        and isinstance(arg.args[0].value, str)
    ):
        return arg.args[0].value, "parse"
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Attribute)
        and arg.func.attr in {"parse", "re"}
        and arg.args
        and isinstance(arg.args[0], ast.Constant)
        and isinstance(arg.args[0].value, str)
    ):
        return arg.args[0].value, arg.func.attr
    return None


def step_definitions(source: str, filename: str) -> list[StepDef]:
    """Find @given/@when/@then decorators in one Python source file."""
    result = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            keyword = _step_keyword(decorator)
            if keyword is None or not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            found = _pattern(decorator.args[0])
            if found:
                pattern, kind = found
                result.append(StepDef(keyword, pattern, kind, node.name, f"{filename}:{node.lineno}"))
    return result


# ------------------------------------------------------------------- feature files
def _substitute(text: str, row: dict[str, str]) -> str:
    for name, value in row.items():
        text = text.replace(f"<{name}>", value)
    return text


def _scenario_children(children: Iterable[Any]) -> Iterable[tuple[str, Any]]:
    for child in children:
        if "background" in child:
            yield "background", child["background"]
        elif "scenario" in child:
            yield "scenario", child["scenario"]
        elif "rule" in child:
            yield from _scenario_children(child["rule"]["children"])


def _uses(steps: Iterable[Any], filename: str, row: dict[str, str]) -> list[StepUse]:
    uses: list[StepUse] = []
    keyword = "given"
    for step in steps:
        keyword = KEYWORD_OF_TYPE.get(step["keywordType"], keyword)  # And/But keep the previous type
        text = _substitute(step["text"], row)
        uses.append(StepUse(keyword, text, f"{filename}:{step['location']['line']}"))
    return uses


def scenarios_in(source: str, filename: str) -> list[ScenarioInfo]:
    document: Any = Parser().parse(TokenScanner(source))
    feature = document.get("feature")
    if not feature:
        return []
    background: list[Any] = []
    result = []
    for kind, node in _scenario_children(feature["children"]):
        if kind == "background":
            background = node["steps"]
            continue
        row: dict[str, str] = {}
        rows = 1
        if node.get("examples"):
            table = node["examples"][0]
            header = [cell["value"] for cell in table["tableHeader"]["cells"]]
            body = table["tableBody"]
            rows = sum(len(e["tableBody"]) for e in node["examples"])
            if body:
                row = dict(zip(header, (cell["value"] for cell in body[0]["cells"]), strict=True))
        steps = _uses(background, filename, row) + _uses(node["steps"], filename, row)
        tags = frozenset(t["name"].lstrip("@") for t in [*feature["tags"], *node["tags"]])
        result.append(
            ScenarioInfo(node["name"], f"{filename}:{node['location']['line']}", tuple(steps), rows, tags)
        )
    return result


# --------------------------------------------------------------------------- rules
def _normalise(pattern: str) -> str:
    return re.sub(r"\{[^}]*\}|<[^>]*>|\"[^\"]*\"", "{}", pattern).lower()


def near_duplicates(
    defs: Sequence[StepDef], ratio: float = NEAR_DUPLICATE_RATIO
) -> list[tuple[StepDef, StepDef, float]]:
    pairs = []
    for i, a in enumerate(defs):
        for b in defs[i + 1 :]:
            if a.keyword != b.keyword:
                continue
            score = SequenceMatcher(None, _normalise(a.pattern), _normalise(b.pattern)).ratio()
            if score >= ratio:
                pairs.append((a, b, round(score, 2)))
    return pairs


def definition_smells(defs: Sequence[StepDef]) -> list[tuple[str, str, str]]:
    return [
        ("greedy-placeholder", d.location, f'`{d.pattern}`: use "{{x:Quoted}}" for quoted values')
        for d in defs
        if d.kind == "parse" and GREEDY_PLACEHOLDER.search(d.pattern)
    ]


def scenario_smells(scenario: ScenarioInfo) -> list[tuple[str, str, str]]:
    smells = []
    where = f"{scenario.location} ({scenario.name})"
    if len(scenario.steps) > MAX_STEPS:
        smells.append(("too-long", where, f"{len(scenario.steps)} steps (max {MAX_STEPS})"))
    whens = sum(1 for s in scenario.steps if s.keyword == "when")
    if whens > 1:
        smells.append(("several-whens", where, f"{whens} When steps: one behaviour per scenario"))
    if not any(s.keyword == "then" for s in scenario.steps):
        smells.append(("no-then", where, "nothing is checked"))
    for step in scenario.steps:
        if IMPERATIVE.search(step.text):
            smells.append(("imperative", step.location, step.text))
        if HARD_CODED_MONEY.search(step.text):
            smells.append(("hard-coded-money", step.location, step.text))
    return smells


def review(defs: list[StepDef], scenarios: list[ScenarioInfo]) -> Review:
    result = Review(defs, scenarios)
    seen_smells: set[tuple[str, str, str]] = set()
    for scenario in scenarios:
        for use in scenario.steps:
            if scenario.manual:
                result.manual_steps.append(use)
                continue
            matches = [d for d in defs if d.keyword == use.keyword and d.matches(use.text)]
            for definition in matches:
                result.usage[definition] += 1
            if not matches:
                result.undefined.append(use)
            elif len(matches) > 1:
                result.ambiguous.append((use, matches))
        for smell in scenario_smells(scenario):
            if smell not in seen_smells:  # background steps repeat in every scenario
                seen_smells.add(smell)
                result.smells.append(smell)
    result.smells += definition_smells(defs)
    result.near_duplicates = near_duplicates(defs)
    return result


# -------------------------------------------------------------------------- report
def to_markdown(r: Review) -> str:
    executable = sum(s.examples for s in r.scenarios)
    lengths = [len(s.steps) for s in r.scenarios] or [0]
    uses = sum(r.usage.values())
    lines = [
        "# BDD review report",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scenarios (as written / executed) | {len(r.scenarios)} / {executable} |",
        f"| Steps per scenario (avg / max) | {sum(lengths) / len(lengths):.1f} / {max(lengths)} |",
        f"| Step definitions | {len(r.definitions)} |",
        f"| Step uses (in scenarios as written) | {uses} |",
        f"| Reuse ratio (uses / definitions) | {uses / max(len(r.definitions), 1):.2f} |",
        f"| Unused definitions | {len(r.unused)} |",
        f"| Undefined steps | {len(r.undefined)} |",
        f"| Steps in @manual scenarios (not automated, by design) | {len(r.manual_steps)} |",
        f"| Ambiguous steps | {len(r.ambiguous)} |",
        f"| Near-duplicate candidates (judge, do not auto-fail) | {len(r.near_duplicates)} |",
        f"| Gherkin smells | {len(r.smells)} |",
        f"| Requirements without scenarios | {len(r.uncovered_requirements)} |",
        "",
        "## Step definition usage",
        "",
        "| Keyword | Pattern | Uses | Location |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {d.keyword} | `{d.pattern}` | {r.usage[d]} | {d.location} |"
        for d in sorted(r.definitions, key=lambda d: (-r.usage[d], d.keyword, d.pattern))
    )
    sections: list[tuple[str, list[str]]] = [
        ("Unused definitions", [f"- `{d.pattern}` ({d.location})" for d in r.unused]),
        ("Undefined steps", [f"- {u.keyword} `{u.text}` ({u.location})" for u in r.undefined]),
        (
            "Ambiguous steps",
            [f"- `{u.text}` matches {[d.pattern for d in ds]} ({u.location})" for u, ds in r.ambiguous],
        ),
        (
            "Near-duplicate candidates (a person decides: merge, rename, or keep)",
            [f"- `{a.pattern}` ~ `{b.pattern}` (similarity {s})" for a, b, s in r.near_duplicates],
        ),
        ("Gherkin smells", [f"- **{rule}** {where}: {detail}" for rule, where, detail in r.smells]),
        ("Requirements without scenarios", [f"- {req}" for req in r.uncovered_requirements]),
    ]
    for title, items in sections:
        lines += ["", f"## {title}", "", *(items or ["None."])]
    return "\n".join(lines) + "\n"


def run(root: Path) -> Review:
    defs = []
    for path in sorted((root / "tests" / "steps").glob("*.py")):
        defs += step_definitions(path.read_text(encoding="utf-8"), str(path.relative_to(root)))
    scenarios = []
    for path in sorted((root / "features").rglob("*.feature")):
        scenarios += scenarios_in(path.read_text(encoding="utf-8"), str(path.relative_to(root)))
    result = review(defs, scenarios)
    registry = load_registry(root / "requirements.toml")
    declared = declared_scenarios(root / "features")
    result.uncovered_requirements = [req for req in registry if req not in declared]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true", help="exit 1 if any problem is found")
    args = parser.parse_args(argv)
    result = run(args.root)
    report = to_markdown(result)
    out = args.root / "reports" / "bdd-review.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Written to {out}. Problems found: {result.problem_count}")
    return 1 if args.strict and result.problem_count else 0


if __name__ == "__main__":
    sys.exit(main())
