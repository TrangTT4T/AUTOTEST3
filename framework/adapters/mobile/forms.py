"""Values typed into the app's checkout forms (data, not screens)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    full_name: str
    line_1: str
    city: str
    zip_code: str
    country: str
    line_2: str = ""
    state: str = ""


@dataclass(frozen=True)
class Card:
    holder: str
    number: str
    expiry: str  # MM/YY
    security_code: str
