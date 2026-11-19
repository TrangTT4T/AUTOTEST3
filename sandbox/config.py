"""Sandbox configuration: timings, and which defects a build contains.

``release`` is the build under test. ``fixed`` is the same code with the defects
corrected; the lab uses it to prove that each defect-detecting test passes once the
defect is gone (Day 12, Part 7).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DEFECTS: dict[str, str] = {
    "per-attempt-payment-key": "the payments worker sends a new idempotency key on every attempt",
    "projector-ignores-sequence": "the read model applies any event whose sequence differs from its version",
    "resume-skips-one-frame": "a WebSocket resume replays frames after since + 1 instead of after since",
}
BUILDS: dict[str, frozenset[str]] = {"release": frozenset(DEFECTS), "fixed": frozenset()}


@dataclass(frozen=True)
class Timings:
    """Short on purpose, so the lab's tests run in seconds. Real systems use larger values."""

    visibility_timeout: float = 0.6  # an unacknowledged message is delivered again after this
    retry_base: float = 0.2  # first retry delay; doubles for each further attempt
    retry_factor: float = 2.0
    max_attempts: int = 3  # then the message goes to the dead-letter queue
    gateway_timeout: float = 0.5  # the payments worker gives up waiting for the gateway
    gateway_latency: float = 0.02
    step_delay: float = 0.05  # packing and shipping each take this long
    consistency_target: float = 2.0  # requirement REQ-13: a status change is visible within 2 s

    def backoff(self, attempt: int) -> float:
        """Delay before the attempt that follows ``attempt`` (1-based)."""
        return self.retry_base * self.retry_factor ** (attempt - 1)


@dataclass(frozen=True)
class Config:
    build: str = "release"
    defects: frozenset[str] = BUILDS["release"]
    timings: Timings = field(default_factory=Timings)
    concurrency: dict[str, int] = field(default_factory=dict)  # worker tasks per subscription (default 1)

    @classmethod
    def for_build(
        cls, build: str, timings: Timings | None = None, concurrency: dict[str, int] | None = None
    ) -> Config:
        if build not in BUILDS:
            raise ValueError(f"unknown build {build!r}; choose one of {sorted(BUILDS)}")
        return cls(build, BUILDS[build], timings or Timings(), dict(concurrency or {}))

    def has(self, defect: str) -> bool:
        return defect in self.defects

    def to_json(self) -> dict[str, Any]:
        # The defect list is NOT published: testers have to find the defects.
        return {"build": self.build, "timings": asdict(self.timings), "concurrency": self.concurrency}
