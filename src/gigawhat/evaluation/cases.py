"""Evaluation cases: questions with the behaviour, sources and notices we expect."""

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from gigawhat.assistant.responses import ResponseKind
from gigawhat.personas import Persona


class Behaviour(StrEnum):
    ANSWER = "answer"
    STRICT = "strict"
    EMERGENCY = "emergency"
    REFUSE = "refuse"
    ABSTAIN = "abstain"


EXPECTED_KINDS = {
    Behaviour.ANSWER: {ResponseKind.ANSWER},
    Behaviour.STRICT: {ResponseKind.PENDING},
    Behaviour.EMERGENCY: {ResponseKind.EMERGENCY},
    Behaviour.REFUSE: {ResponseKind.REFUSAL},
    Behaviour.ABSTAIN: {ResponseKind.ABSTAIN},
}


class Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    question: str
    persona: Persona
    tier: str
    behaviour: Behaviour
    must_cite: tuple[str, ...] = ()
    must_not_cite: tuple[str, ...] = ()
    notices: tuple[str, ...] = ()
    reference: str = ""
    why: str = ""
    pii: bool = False


def load_cases(path: Path) -> list[Case]:
    return [Case.model_validate(raw) for raw in yaml.safe_load(path.read_text())["cases"]]
