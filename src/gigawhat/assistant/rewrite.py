"""Rewrites a conversational question into the formal terms procedures use, to help search."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from gigawhat.assistant.prompts import REWRITE_PROMPT

MAX_REWRITES = 2


class SearchQueries(BaseModel):
    queries: list[str] = Field(description="One or two short search queries.")


async def rewrite_queries(model: BaseChatModel, question: str) -> tuple[str, ...]:
    writer = model.with_structured_output(SearchQueries, method="json_schema")
    result = await writer.ainvoke([SystemMessage(REWRITE_PROMPT), HumanMessage(question)])
    queries = SearchQueries.model_validate(result).queries
    return tuple(query.strip() for query in queries[:MAX_REWRITES] if query.strip())
