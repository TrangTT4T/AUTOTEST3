"""Selector conventions for the web page objects (Unit 2; locator style aligned with the team's).

Every page object and component declares its selectors as STRING CONSTANTS in a
``# --- Locators ---`` section at the bottom of the class, and its methods only use
those names. Dynamic selectors are templates filled with ``.format(...)``.

Playwright selector strings used here (all built into Playwright):

| Form | Example | Matches |
|---|---|---|
| CSS | ``#product-price`` | standard CSS |
| ``role=`` | ``role=button[name='Add to Cart']`` | role + accessible name, full name, any case |
| ``role=`` + ``s`` | ``role=link[name="Blue jacket" s]`` | the name exactly, case-sensitive |
| ``role=`` + regex | ``role=link[name=/^My Cart \\(\\d+\\)$/]`` | the name by regular expression |
| ``text=`` | ``text=No results found for`` | visible text containing it, ignoring case |
| chain ``>>`` | ``role=banner >> role=textbox[name='Search']`` | the right part inside the left part |
"""

from __future__ import annotations

import json


def quoted(text: str) -> str:
    """Quote a value (from data, e.g. a product name) for a selector attribute, escaping quotes."""
    return json.dumps(text)
