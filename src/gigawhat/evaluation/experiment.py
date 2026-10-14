"""Evaluation as a LangSmith experiment, the way LangSmith documents it.

The cases are a dataset, one example per case, split by suite. The assistant is the target; the
deterministic checks are an evaluator that scores each run; the release gates are a summary
evaluator that scores the experiment. LangSmith keeps every experiment, so runs can be compared
side by side, and each score links to the trace behind it.

Personal data never goes to LangSmith: the dataset holds each question masked, and the target and
the scoring use the local, unmasked case, looked up by its id. The assistant then masks the
question itself before anything is traced, as it does for a user.

Cloud profile only: aevaluate calls LangSmith even with upload_results=False, so the offline
profile evaluates with the local runner instead.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Any

from langsmith import Client, aevaluate
from langsmith.evaluation import EvaluationResult, EvaluationResults
from langsmith.schemas import Example, Run

from gigawhat.evaluation.cases import Case
from gigawhat.evaluation.checks import CaseResult, Outcome, score
from gigawhat.evaluation.judge import SCORE_NAMES, judge_answer
from gigawhat.evaluation.report import gates
from gigawhat.evaluation.runner import Evaluation, EvaluationPlan, Evaluator, Experiment
from gigawhat.orchestration.responses import ResponseKind
from gigawhat.policy.pii import pii_masker

DATASET = "gigawhat-evaluation"
DATASET_DESCRIPTION = (
    "GigaWhat golden and red-team cases from evals/*.yaml (fictional data; questions masked)"
)
RowEvaluator = Callable[[Run, Example], Awaitable[EvaluationResults]]


@dataclass(frozen=True)
class Scoring:
    """Scores runs against the local cases. LangSmith holds only masked questions, but the
    personal-data check needs the original question to know what must not be repeated."""

    cases: dict[str, Case]

    def case_result(self, run: Run, example: Example) -> CaseResult:
        case = self.cases[(example.metadata or {})["case_id"]]
        if run.error or not run.outputs:
            return CaseResult(
                case, "error", None, 0.0, error=run.error or "the run returned nothing"
            )
        return score(case, Outcome.model_validate(run.outputs))

    def case_checks(self, run: Run, example: Example) -> EvaluationResults:
        """Every check that applies to the case, as a LangSmith score of 1 (passed) or 0."""
        return _results(self.case_result(run, example).checks())

    def release_gates(self, runs: list[Run], examples: list[Example]) -> EvaluationResults:
        """The release gates over the whole experiment, as LangSmith summary scores."""
        results = [self.case_result(run, ex) for run, ex in zip(runs, examples, strict=True)]
        return EvaluationResults(
            results=[
                EvaluationResult(key=gate.name, score=gate.passed, comment=gate.detail)
                for gate in gates(results)
            ]
        )

    def judged_by(self, judge: Any) -> RowEvaluator:
        """DeepEval's faithfulness and relevancy for answers, as LangSmith scores."""

        async def deepeval(run: Run, example: Example) -> EvaluationResults:
            result = self.case_result(run, example)
            if result.kind != ResponseKind.ANSWER or not run.outputs:
                return _results({})
            outcome = Outcome.model_validate(run.outputs)
            return _results(await judge_answer(judge, result.case, outcome))

        return deepeval


async def run_experiment(evaluator: Evaluator, plan: EvaluationPlan, client: Client) -> Evaluation:
    cases = {case.id: case for suite in plan.suites.values() for case in suite}
    scoring = Scoring(cases)
    examples = sync_dataset(client, plan.suites)

    async def target(inputs: dict[str, Any]) -> dict[str, Any]:
        case = cases[inputs["case_id"]]
        outcome = await evaluator.outcome(case.question, case.persona)
        return outcome.model_dump(mode="json")

    row_evaluators: list[Any] = [scoring.case_checks]
    if evaluator.judge is not None:
        row_evaluators.append(scoring.judged_by(evaluator.judge))
    experiment = await aevaluate(
        target,
        data=[examples[case.id] for case in plan.cases],
        evaluators=row_evaluators,
        summary_evaluators=[scoring.release_gates],
        experiment_prefix="+".join(plan.suites),
        metadata={"limit": plan.limit, **evaluator.assistant.trace_metadata},
        max_concurrency=plan.concurrency,
        client=client,
    )
    by_case = {}
    async for row in experiment:
        result = scoring.case_result(row["run"], row["example"])
        by_case[result.case.id] = _with_judge_scores(result, row["evaluation_results"]["results"])
    client.flush()
    name = experiment.experiment_name
    url = client.read_project(project_name=name).url
    return Evaluation([by_case[case.id] for case in plan.cases], Experiment(name, url))


def sync_dataset(client: Client, suites: dict[str, list[Case]]) -> dict[str, Example]:
    """Makes the dataset match the suites' YAML, which stays the one source of truth, and
    returns each case's example by case id. Suites not being run are left alone."""
    if not client.has_dataset(dataset_name=DATASET):
        client.create_dataset(DATASET, description=DATASET_DESCRIPTION)
    wanted = {
        case.id: example_fields(case, suite) for suite, cases in suites.items() for case in cases
    }
    stored = _stored_examples(client, list(suites))
    missing = [fields for case_id, fields in wanted.items() if case_id not in stored]
    if missing:
        client.create_examples(dataset_name=DATASET, examples=missing)
    for case_id, example in stored.items():
        if case_id in wanted and _differs(example, wanted[case_id]):
            client.update_example(example.id, **wanted[case_id])
    removed = [example.id for case_id, example in stored.items() if case_id not in wanted]
    if removed:
        client.delete_examples(removed)
    return _stored_examples(client, list(suites))


def example_fields(case: Case, suite: str) -> dict[str, Any]:
    """A case as a dataset example: the masked question and the persona go in; the expectations
    are the reference outputs."""
    inputs = {
        "case_id": case.id,
        "question": pii_masker().mask(case.question).text,
        "persona": case.persona.value,
    }
    outputs = case.model_dump(mode="json", exclude={"id", "question", "persona", "why"})
    metadata = {"case_id": case.id, "why": case.why}
    return {"inputs": inputs, "outputs": outputs, "metadata": metadata, "split": suite}


def _results(scores: dict[str, bool] | dict[str, float]) -> EvaluationResults:
    return EvaluationResults(
        results=[EvaluationResult(key=name, score=value) for name, value in scores.items()]
    )


def _stored_examples(client: Client, splits: list[str]) -> dict[str, Example]:
    examples = client.list_examples(dataset_name=DATASET, splits=splits)
    return {(example.metadata or {})["case_id"]: example for example in examples}


def _differs(example: Example, fields: dict[str, Any]) -> bool:
    metadata = example.metadata or {}
    return (
        example.inputs != fields["inputs"]
        or example.outputs != fields["outputs"]
        or any(metadata.get(name) != value for name, value in fields["metadata"].items())
    )


def _with_judge_scores(result: CaseResult, evaluations: list[EvaluationResult]) -> CaseResult:
    scores = {e.key: e.score for e in evaluations if e.key in SCORE_NAMES and e.score is not None}
    return replace(result, scores=scores) if scores else result
