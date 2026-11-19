"""``covers``: link a plain pytest test to requirements, for the traceability matrix.

    @covers("REQ-03", "REQ-04")
    def test_customer_buys_two_products(...): ...

The matrix counts every test whose report carries a ``REQ-xx`` keyword, so
end-to-end tests add evidence to the same requirements as the BDD scenarios.
The ids are registered markers (from requirements.toml), so a typo fails the run.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pytest

F = TypeVar("F", bound=Callable[..., object])


def covers(*requirement_ids: str) -> Callable[[F], F]:
    def apply(test: F) -> F:
        for requirement_id in requirement_ids:
            test = getattr(pytest.mark, requirement_id)(test)
        return test

    return apply
