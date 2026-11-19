"""Test data builders: unique, valid data on demand, never shared between tests."""

from __future__ import annotations

import secrets

from framework.domain import Customer


def unique_email(prefix: str = "qa") -> str:
    """An address that is unique per call and clearly marked as test data.

    example.com is reserved for documentation (RFC 2606): mail to it is never delivered.
    """
    return f"{prefix}+{secrets.token_hex(6)}@example.com"


def new_customer(**overrides: str) -> Customer:
    values = {
        "first_name": "Test",
        "last_name": "Customer",
        "email": unique_email(),
        "password": f"Pw-{secrets.token_urlsafe(12)}",
    }
    values.update(overrides)
    return Customer(**values)
