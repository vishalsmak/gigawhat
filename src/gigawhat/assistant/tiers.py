"""Safety tiers. Fixed rules set a floor; a model classifies too; the stricter result wins."""

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from gigawhat.assistant.prompts import TIER_PROMPT


class Tier(StrEnum):
    ROUTINE = "routine"
    SAFETY_RELEVANT = "safety_relevant"
    SAFETY_CRITICAL = "safety_critical"
    EMERGENCY = "emergency"


SEVERITY = {tier: rank for rank, tier in enumerate(Tier)}


def stricter(first: Tier, second: Tier) -> Tier:
    return first if SEVERITY[first] >= SEVERITY[second] else second


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class RuleVerdict:
    tier: Tier
    matched: tuple[str, ...]


@dataclass(frozen=True)
class TierRules:
    emergency: tuple[Rule, ...]
    critical_intent: re.Pattern[str]
    critical_topics: tuple[Rule, ...]
    relevant: tuple[Rule, ...]

    def classify(self, question: str) -> RuleVerdict:
        for tier, rules in self._tiers_by_severity(question):
            matched = tuple(rule.rule_id for rule in rules if rule.pattern.search(question))
            if matched:
                return RuleVerdict(tier, matched)
        return RuleVerdict(Tier.ROUTINE, ())

    def _tiers_by_severity(self, question: str) -> list[tuple[Tier, tuple[Rule, ...]]]:
        wants_to_act = bool(self.critical_intent.search(question))
        critical = self.critical_topics if wants_to_act else ()
        return [
            (Tier.EMERGENCY, self.emergency),
            (Tier.SAFETY_CRITICAL, critical),
            (Tier.SAFETY_RELEVANT, self.relevant),
        ]


class TierDecision(BaseModel):
    tier: Tier = Field(description="The safety tier of the question.")
    reason: str = Field(description="One sentence explaining the choice.")


@cache
def tier_rules() -> TierRules:
    source = resources.files("gigawhat.assistant").joinpath("safety_topics.yaml").read_text()
    raw = yaml.safe_load(source)
    critical = raw["safety_critical"]
    return TierRules(
        emergency=_rules(raw["emergency"]),
        critical_intent=re.compile(critical["intent"], re.IGNORECASE),
        critical_topics=_rules(critical["topics"]),
        relevant=_rules(raw["safety_relevant"]),
    )


async def classify_with_model(model: BaseChatModel, question: str) -> TierDecision:
    classifier = model.with_structured_output(TierDecision, method="json_schema")
    decision = await classifier.ainvoke([SystemMessage(TIER_PROMPT), HumanMessage(question)])
    return TierDecision.model_validate(decision)


def _rules(entries: list[dict[str, str]]) -> tuple[Rule, ...]:
    return tuple(
        Rule(entry["id"], re.compile(entry["pattern"], re.IGNORECASE)) for entry in entries
    )
