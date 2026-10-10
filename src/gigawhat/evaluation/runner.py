"""Runs evaluation cases through the real assistant."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from gigawhat.assistant.pii import pii_masker
from gigawhat.assistant.responses import ResponseKind
from gigawhat.assistant.service import Assistant, Question
from gigawhat.evaluation.cases import Case
from gigawhat.evaluation.checks import CaseResult, Observation, score
from gigawhat.evaluation.judge import judge_answer


@dataclass(frozen=True)
class Evaluator:
    assistant: Assistant
    judge: Any = None
    visitor: str = field(default_factory=lambda: f"eval-{uuid.uuid4().hex[:8]}")

    async def run(self, case: Case) -> CaseResult:
        personal_data = tuple(pii_masker().find(case.question)) if case.pii else ()
        started = time.monotonic()
        try:
            turn = await self.assistant.ask(Question(case.question, case.persona, self.visitor))
        except Exception as error:  # A crashed case is reported, not allowed to stop the run.
            return CaseResult(case, "error", None, time.monotonic() - started, error=repr(error))
        result = score(case, Observation(turn, time.monotonic() - started, personal_data))
        if self.judge is not None and turn.response.kind == ResponseKind.ANSWER:
            result = replace(result, scores=await judge_answer(self.judge, case, turn))
        return result


async def run_cases(evaluator: Evaluator, cases: list[Case], concurrency: int) -> list[CaseResult]:
    limit = asyncio.Semaphore(concurrency)

    async def run(case: Case) -> CaseResult:
        async with limit:
            return await evaluator.run(case)

    return list(await asyncio.gather(*(run(case) for case in cases)))
