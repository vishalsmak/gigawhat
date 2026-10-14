import time

from gigawhat.config import ModelChoice, Provider
from gigawhat.providers.limits import (
    GEMINI_FREE_FLASH_LITE,
    RollingWindowRateLimiter,
    shared_limiter,
)

WINDOW = 60.0


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def limiter_with(clock: FakeClock, requests: int = 2) -> RollingWindowRateLimiter:
    return RollingWindowRateLimiter(requests, WINDOW, clock)


def test_requests_up_to_the_limit_go_straight_through() -> None:
    limiter = limiter_with(FakeClock())

    assert [limiter.acquire(blocking=False) for _ in range(2)] == [True, True]


def test_request_over_the_limit_must_wait() -> None:
    limiter = limiter_with(FakeClock())
    limiter.acquire()
    limiter.acquire()

    assert limiter.acquire(blocking=False) is False


def test_slot_frees_once_the_oldest_request_leaves_the_window() -> None:
    clock = FakeClock()
    limiter = limiter_with(clock)
    limiter.acquire()
    limiter.acquire()

    clock.now += WINDOW

    assert limiter.acquire(blocking=False) is True


def test_slot_stays_taken_just_inside_the_window() -> None:
    clock = FakeClock()
    limiter = limiter_with(clock)
    limiter.acquire()
    limiter.acquire()

    clock.now += WINDOW - 0.001

    assert limiter.acquire(blocking=False) is False


async def test_blocked_request_waits_for_a_free_slot() -> None:
    limiter = RollingWindowRateLimiter(requests=1, window_seconds=0.05)
    await limiter.aacquire()
    started = time.monotonic()

    await limiter.aacquire()

    assert time.monotonic() - started >= 0.04


def test_model_with_declared_limits_gets_one_limiter_per_process() -> None:
    choice = ModelChoice(Provider.GEMINI, "gemini-3.5-flash-lite")

    assert shared_limiter(choice) is shared_limiter(ModelChoice(Provider.GEMINI, choice.name))


def test_model_without_declared_limits_is_not_paced() -> None:
    assert shared_limiter(ModelChoice(Provider.OLLAMA, "gpt-oss:20b")) is None


def test_limits_read_as_a_sentence() -> None:
    assert str(GEMINI_FREE_FLASH_LITE) == (
        "15 requests/min, 250,000 tokens/min, 500 requests/day (Gemini free tier)"
    )
