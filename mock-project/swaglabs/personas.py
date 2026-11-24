"""The demo accounts ("personas") of Swag Labs.

Each persona is the same shop with different built-in behaviour, which makes them a ready-made
fault-injection matrix: the suite runs once per persona (``--persona``) and the findings register
says which scenarios each persona is expected to break.
"""

from __future__ import annotations

from enum import StrEnum


class Persona(StrEnum):
    STANDARD = "standard_user"
    LOCKED_OUT = "locked_out_user"
    PROBLEM = "problem_user"
    PERFORMANCE_GLITCH = "performance_glitch_user"
    ERROR = "error_user"
    VISUAL = "visual_user"

    @property
    def can_log_in(self) -> bool:
        return self is not Persona.LOCKED_OUT

    @classmethod
    def runnable(cls) -> list[Persona]:
        """Personas the whole suite can run as (a locked-out user cannot get past the login page)."""
        return [p for p in cls if p.can_log_in]

    @classmethod
    def parse(cls, name: str) -> Persona:
        try:
            return cls(name)
        except ValueError:
            raise ValueError(f"unknown persona {name!r}; one of {[p.value for p in cls]}") from None
