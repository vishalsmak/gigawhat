"""One assistant per process, shared by the chat UI and the HTTP API."""

import asyncio

from gigawhat.config import get_settings
from gigawhat.observability.tracing import create_tracer
from gigawhat.orchestration.service import Assistant, create_assistant
from gigawhat.ui.limits import RateLimiter

_assistant: Assistant | None = None
_lock = asyncio.Lock()
limiter = RateLimiter(get_settings().questions_per_hour)


async def get_assistant() -> Assistant:
    global _assistant
    async with _lock:
        if _assistant is None:
            settings = get_settings()
            _assistant = await create_assistant(settings, create_tracer(settings))
    return _assistant


async def close_assistant() -> None:
    global _assistant
    async with _lock:
        if _assistant is not None:
            await _assistant.aclose()
            _assistant = None
