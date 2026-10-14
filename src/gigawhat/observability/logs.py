"""Structured logs: one JSON line per event, carrying the context of the question behind it.

Context such as the thread and persona is bound once (`bind_contextvars`) and every line written
while that question runs carries it. Logs hold ids, categories and timings, never what anyone
typed or what the assistant wrote: the audit trail keeps those, masked and under access control.
A processor withholds such fields if one is ever logged by mistake.
"""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

# Fields that could hold what a person typed or what the assistant wrote.
CONTENT_FIELDS = frozenset({"question", "note", "text", "answer", "extract", "prompt"})
WITHHELD = "[withheld]"


def withhold_content(
    logger: Any, method_name: str, event: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for field in CONTENT_FIELDS & event.keys():
        event[field] = WITHHELD
    return event


def configure_logging(level: str) -> None:
    """JSON lines on stderr from `level` up, e.g. "INFO" for the server, "WARNING" for the CLI.

    Loggers are not cached on first use: at a few lines per question the saving is nothing, and
    caching would freeze this configuration in every module that had already logged.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            withhold_content,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
