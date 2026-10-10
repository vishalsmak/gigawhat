"""Model-judged quality with DeepEval: is an answer faithful to its sources, and relevant?"""

import os
from typing import Any

from langchain_core.language_models import BaseChatModel

from gigawhat.assistant.service import Turn
from gigawhat.evaluation.cases import Case

THRESHOLD = 0.7


def build_judge(model: BaseChatModel, name: str) -> Any:
    # Set before DeepEval is imported: it sends usage telemetry and loads .env unless told not to.
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
    os.environ.setdefault("DEEPEVAL_DISABLE_DOTENV", "1")
    from deepeval.models import DeepEvalBaseLLM

    class LangChainJudge(DeepEvalBaseLLM):
        """Lets DeepEval use our configured chat model as its judge. Signatures follow
        DeepEvalBaseLLM, which passes the prompt positionally."""

        def load_model(self, *args: Any, **kwargs: Any) -> "LangChainJudge":
            return self

        def generate(self, prompt: str) -> str:
            return str(model.invoke(prompt).content)

        async def a_generate(self, prompt: str) -> str:
            return str((await model.ainvoke(prompt)).content)

        def generate_with_schema(self, *args: Any, schema: Any = None, **kwargs: Any) -> Any:
            return model.with_structured_output(schema, method="json_schema").invoke(args[0])

        async def a_generate_with_schema(
            self, *args: Any, schema: Any = None, **kwargs: Any
        ) -> Any:
            writer = model.with_structured_output(schema, method="json_schema")
            return await writer.ainvoke(args[0])

        def get_model_name(self, *args: Any, **kwargs: Any) -> str:
            return name

    return LangChainJudge()


async def judge_answer(judge: Any, case: Case, turn: Turn) -> dict[str, float]:
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    test_case = LLMTestCase(
        input=case.question,
        actual_output=turn.response.text,
        retrieval_context=[source.text for source in turn.response.sources],
    )
    faithfulness = FaithfulnessMetric(threshold=THRESHOLD, model=judge, include_reason=False)
    relevancy = AnswerRelevancyMetric(threshold=THRESHOLD, model=judge, include_reason=False)
    await faithfulness.a_measure(test_case, _show_indicator=False)
    await relevancy.a_measure(test_case, _show_indicator=False)
    return {"faithfulness": faithfulness.score or 0.0, "relevancy": relevancy.score or 0.0}
