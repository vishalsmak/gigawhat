"""Providers' rate limits, and pacing requests to stay under them.

No provider reports its limits through its API, so they are declared here with their source.
Limits apply per model, so each model gets one limiter, shared by every role that uses it.
"""

import asyncio
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache

from langchain_core.rate_limiters import BaseRateLimiter

from gigawhat.config import ModelChoice, Provider

SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True)
class RateLimits:
    requests_per_minute: int
    tokens_per_minute: int
    requests_per_day: int
    source: str

    def __str__(self) -> str:
        return (
            f"{self.requests_per_minute} requests/min, {self.tokens_per_minute:,} tokens/min, "
            f"{self.requests_per_day:,} requests/day ({self.source})"
        )


# Google no longer publishes free-tier limits. Requests are as measured from its 429 errors on
# 2 September 2026; tokens a minute is its last published figure (2025). Daily quotas reset at
# midnight Pacific time.
GEMINI_FREE_FLASH_LITE = RateLimits(15, 250_000, 500, "Gemini free tier")
GROQ_FREE = RateLimits(30, 8_000, 1_000, "Groq free plan")
DECLARED_LIMITS = {
    ModelChoice(Provider.GEMINI, "gemini-3.1-flash-lite"): GEMINI_FREE_FLASH_LITE,
    ModelChoice(Provider.GEMINI, "gemini-3.5-flash-lite"): GEMINI_FREE_FLASH_LITE,
    ModelChoice(Provider.GROQ, "openai/gpt-oss-20b"): GROQ_FREE,
}


class RollingWindowRateLimiter(BaseRateLimiter):
    """At most `requests` calls in any window, which is how providers count requests a minute.

    Unlike a token bucket, a question's few calls go straight through; only sustained load,
    such as an evaluation, waits.
    """

    def __init__(
        self,
        requests: int,
        window_seconds: float = SECONDS_PER_MINUTE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._requests = requests
        self._window = window_seconds
        self._clock = clock
        self._sent: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, *, blocking: bool = True) -> bool:
        while (wait := self._reserve()) > 0:
            if not blocking:
                return False
            time.sleep(wait)
        return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        while (wait := self._reserve()) > 0:
            if not blocking:
                return False
            await asyncio.sleep(wait)
        return True

    def _reserve(self) -> float:
        """Claims a slot and returns 0, or returns the seconds until one frees up."""
        with self._lock:
            now = self._clock()
            while self._sent and now - self._sent[0] >= self._window:
                self._sent.popleft()
            if len(self._sent) < self._requests:
                self._sent.append(now)
                return 0.0
            return self._window - (now - self._sent[0])


@cache
def shared_limiter(choice: ModelChoice) -> BaseRateLimiter | None:
    """One limiter per model in this process, so every role and registry using it pace together.
    None when the model has no declared limits."""
    limits = DECLARED_LIMITS.get(choice)
    return RollingWindowRateLimiter(limits.requests_per_minute) if limits else None
