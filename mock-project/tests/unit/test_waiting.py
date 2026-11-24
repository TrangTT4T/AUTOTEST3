import pytest

from swaglabs.waiting import eventually


class FakeClock:
    """Time that only moves when the code under test sleeps: deterministic and instant."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(round(seconds, 3))
        self.now += seconds


def test_returns_as_soon_as_the_predicate_holds() -> None:
    clock = FakeClock()
    values = iter([1, 2, 3, 4])
    result = eventually(
        lambda: next(values), lambda v: v >= 3, timeout_s=5, description="d", clock=clock, sleep=clock.sleep
    )
    assert result == 3
    assert clock.sleeps == [0.1, 0.15]  # backs off between tries


def test_waits_grow_up_to_the_cap_and_never_overshoot_the_deadline() -> None:
    clock = FakeClock()
    with pytest.raises(AssertionError, match=r"not reached within 2 s .*last value: 0"):
        eventually(
            lambda: 0,
            lambda v: v > 0,
            timeout_s=2,
            description="counter should grow",
            max_interval_s=0.5,
            clock=clock,
            sleep=clock.sleep,
        )
    assert max(clock.sleeps) == 0.5
    assert clock.now == pytest.approx(2.0)


def test_failure_message_names_the_expectation() -> None:
    clock = FakeClock()
    with pytest.raises(AssertionError, match="stored cart should hold"):
        eventually(
            list,
            bool,
            timeout_s=0.3,
            description="stored cart should hold [4]",
            clock=clock,
            sleep=clock.sleep,
        )


@pytest.mark.parametrize(
    "kwargs", [{"timeout_s": 0}, {"timeout_s": 1, "interval_s": 0}, {"timeout_s": 1, "backoff": 0.5}]
)
def test_rejects_nonsense_settings(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="positive"):
        eventually(lambda: 1, bool, description="d", **kwargs)  # type: ignore[arg-type]
