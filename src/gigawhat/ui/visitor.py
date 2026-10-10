"""Anonymous visitor identity for the demo: a random ID in a cookie, no sign-up."""

import secrets
from http.cookies import SimpleCookie

VISITOR_COOKIE = "gw_visitor"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def new_visitor_id() -> str:
    return secrets.token_urlsafe(16)


def visitor_from_cookie_header(header: str | None) -> str | None:
    if not header:
        return None
    cookie = SimpleCookie()
    cookie.load(header)
    morsel = cookie.get(VISITOR_COOKIE)
    return morsel.value if morsel else None
