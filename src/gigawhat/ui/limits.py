"""A per-visitor question limit, so an open demo link can't run up the model bill."""

import time
from collections import defaultdict, deque

WINDOW_SECONDS = 3600


class RateLimiter:
    def __init__(self, per_hour: int) -> None:
        self._per_hour = per_hour
        self._asked: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, visitor_id: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        asked = self._asked[visitor_id]
        while asked and moment - asked[0] >= WINDOW_SECONDS:
            asked.popleft()
        if len(asked) >= self._per_hour:
            return False
        asked.append(moment)
        return True
