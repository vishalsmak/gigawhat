"""Runs evaluation cases through the real assistant, on this machine.

On the cloud profile with a LangSmith key, evaluation/experiment.py runs the same cases as a
LangSmith experiment instead; both score with the same checks and gates.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from gigawhat.evaluation.cases import Case
from gigawhat.evaluation.checks import CaseResult, Outcome, score
from gigawhat.evaluation.judge import judge_answer
from gigawhat.identity.personas import Persona
from gigawhat.orchestration.responses import ResponseKind
from gigawhat.orchestration.service import Assistant, Question


@dataclass(frozen=True)
class EvaluationPlan:
    suites: dict[str, list[Case]]
    limit: int | None = None
    concurrency: int = 1
    judge: bool = False

    @property
    def cases(self) -> list[Case]:
        """The first `limit` cases of each suite, or all of them."""
        return [case for cases in self.suites.values() for case in cases[: self.limit]]


@dataclass(frozen=True)
class Experiment:
    """Where a run's traces and scores are in LangSmith. The URL holds the account's
    organisation ID, so reports, which are committed, show only the name."""

    name: str
    url: str


@dataclass(frozen=True)
class Evaluation:
    results: list[CaseResult]
    experiment: Experiment | None = None


@dataclass(frozen=True)
class Evaluator:
    assistant: Assistant
    judge: Any = None
    visitor: str = field(default_factory=lambda: f"eval-{uuid.uuid4().hex[:8]}")

    async def outcome(self, question: str, persona: Persona) -> Outcome:
        """Asks the assistant, exactly as a user would. This is what an evaluation tests."""
        started = time.monotonic()
        turn = await self.assistant.ask(Question(question, persona, self.visitor))
        return Outcome.of(turn, time.monotonic() - started)

    async def run(self, case: Case) -> CaseResult:
        started = time.monotonic()
        try:
            outcome = await self.outcome(case.question, case.persona)
        except Exception as error:  # A crashed case is reported, not allowed to stop the run.
            return CaseResult(case, "error", None, time.monotonic() - started, error=repr(error))
        result = score(case, outcome)
        if self.judge is not None and outcome.response.kind == ResponseKind.ANSWER:
            result = replace(result, scores=await judge_answer(self.judge, case, outcome))
        return result


async def run_cases(evaluator: Evaluator, cases: list[Case], concurrency: int) -> list[CaseResult]:
    limit = asyncio.Semaphore(concurrency)

    async def run(case: Case) -> CaseResult:
        async with limit:
            return await evaluator.run(case)

    return list(await asyncio.gather(*(run(case) for case in cases)))
