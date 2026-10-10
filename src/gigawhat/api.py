"""HTTP entry point: health check, the visitor's audit export, and the Chainlit chat UI."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from chainlit.utils import mount_chainlit
from fastapi import FastAPI, Request, Response

from gigawhat.config import get_settings
from gigawhat.ui.runtime import close_assistant, get_assistant
from gigawhat.ui.visitor import (
    VISITOR_COOKIE,
    VISITOR_COOKIE_MAX_AGE,
    new_visitor_id,
    visitor_from_cookie_header,
)

CHAT_MODULE = Path(__file__).parent / "ui" / "chat.py"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_assistant()
    yield
    await close_assistant()


app = FastAPI(title="GigaWhat", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware("http")
async def visitor_cookie(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Give each browser a random visitor ID: chats, requests and audit stay per browser."""
    response = await call_next(request)
    if VISITOR_COOKIE not in request.cookies:
        response.set_cookie(
            VISITOR_COOKIE,
            new_visitor_id(),
            max_age=VISITOR_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "profile": get_settings().profile.value}


@app.get("/api/audit")
async def audit(request: Request) -> list[dict[str, Any]]:
    """This browser's audit events, newest first. Outside demo mode, everyone's."""
    assistant = await get_assistant()
    visitor = visitor_from_cookie_header(request.headers.get("cookie"))
    if get_settings().demo_mode and visitor is None:
        return []
    return await assistant.oversight.events_for(visitor if get_settings().demo_mode else None)


mount_chainlit(app=app, target=str(CHAT_MODULE), path="/")
