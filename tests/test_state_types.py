"""Every project type saved in graph state must be on the checkpoint allowlist. A type that isn't
comes back from Postgres as a plain dict, with only a log warning to say so."""

import dataclasses
import typing
from enum import Enum

from pydantic import BaseModel

from gigawhat.assistant.graph import STATE_TYPES, AssistantState


def project_classes(annotation: object) -> set[type]:
    """Project classes named anywhere in a type annotation, such as list[Passage] | None."""
    found: set[type] = set()
    if isinstance(annotation, type) and annotation.__module__.startswith("gigawhat"):
        found.add(annotation)
    for argument in typing.get_args(annotation):
        found |= project_classes(argument)
    return found


def field_annotations(cls: type) -> list[object]:
    if dataclasses.is_dataclass(cls):
        return list(typing.get_type_hints(cls).values())
    if issubclass(cls, BaseModel):
        return [info.annotation for info in cls.model_fields.values()]
    return []


def reachable_from_state() -> set[type]:
    pending = set().union(
        *(project_classes(a) for a in typing.get_type_hints(AssistantState).values())
    )
    seen: set[type] = set()
    while pending:
        cls = pending.pop()
        seen.add(cls)
        for annotation in field_annotations(cls):
            pending |= project_classes(annotation) - seen
    return seen


def test_every_type_in_graph_state_is_allowed_through_the_checkpoint() -> None:
    allowed = set(STATE_TYPES)
    stored = {
        cls
        for cls in reachable_from_state()
        if dataclasses.is_dataclass(cls) or issubclass(cls, (BaseModel, Enum))
    }

    missing = sorted(
        cls.__name__ for cls in stored if (cls.__module__, cls.__name__) not in allowed
    )

    assert missing == []
