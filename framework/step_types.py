"""Shared parse types for step patterns.

Why: a plain ``"{name}"`` placeholder is greedy. In
``the cart contains {quantity:d} "{name}"`` it also matches
``the cart contains 1 "Noir jacket" in variant "L / Red"`` with
name = ``Noir jacket" in variant "L / Red``. pytest-bdd does not report the
clash; it silently picks one definition, in an order nobody chose.

Every quoted placeholder therefore uses ``{x:Quoted}``, which never crosses a
quote, and every pattern is built with ``parsed(...)`` so the type is known.
The review tool (framework/review.py) enforces both rules.
"""

from __future__ import annotations

from pytest_bdd import parsers


class _Quoted:
    """parse type: any text without a double quote (what ``@parse.with_pattern`` would build)."""

    pattern = r'[^"]*'

    def __call__(self, text: str) -> str:
        return text


STEP_TYPES = {"Quoted": _Quoted()}


def parsed(pattern: str) -> parsers.parse:
    """A pytest-bdd parse pattern that knows the shared types."""
    return parsers.parse(pattern, extra_types=STEP_TYPES)
