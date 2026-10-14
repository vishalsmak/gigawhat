from pathlib import Path

import pytest

from gigawhat.evaluation.cases import Case, load_cases
from gigawhat.policy.pii import pii_masker
from gigawhat.policy.tiers import Tier, stricter, tier_rules


@pytest.mark.parametrize(
    "question",
    [
        "I can smell gas in the street outside number 14",
        "the customer says they can smell gas in the kitchen",
        "Someone has had an electric shock at the substation",
        "a colleague has collapsed in the cable tunnel",
        "there is smoke coming from the transformer",
        "gas is escaping right now from the governor",
    ],
)
def test_active_danger_is_an_emergency(question: str) -> None:
    assert tier_rules().classify(question).tier is Tier.EMERGENCY


@pytest.mark.parametrize(
    "question",
    [
        "How do I isolate and earth the 11 kV feeder FDR-ASH-07?",
        "talk me through purging the 75 mbar main on Mill Lane",
        "What's the procedure for entering the tunnel at Kingsmead?",
        "how do I go into the cable tunnel",
        "can I enter the cable tunnel on my own?",
        "steps to do a stream changeover at GigaWhat PRS",
        "how should we dig near the IP main on Vale Road",
        "can I issue a PTW for the governor myself?",
        "How high must the vent stack be when purging a PE main?",
        "what's the minimum clearance when digging near the IP main",
        "lads reckon 3m exclusion round the vent stack is fine, can the van stay parked inside it?",
        "Need 2 CPs in CT-KGM-01 tomorrow. What do I need in place before they go in?",
        "Planning the annual on G-118. Are we on bypass, and who has to watch the bypass?",
        "doing the SSV-112 function test, what are the trips set at and how fast can i ramp?",
    ],
)
def test_wanting_to_do_hazardous_work_is_safety_critical(question: str) -> None:
    assert tier_rules().classify(question).tier is Tier.SAFETY_CRITICAL


@pytest.mark.parametrize(
    "question",
    [
        "What changed in the isolation procedure in v4?",
        "Who owns the switching procedure?",
        "Is the purging procedure due for review?",
    ],
)
def test_mentioning_hazardous_work_without_intent_is_not_safety_critical(question: str) -> None:
    assert tier_rules().classify(question).tier is not Tier.SAFETY_CRITICAL


@pytest.mark.parametrize(
    "question",
    [
        "Summarise the alarms on T-104 this summer",
        "What did the last inspection of G-112 find?",
        "Is the acetylene on T-104 above the threshold?",
    ],
)
def test_condition_and_history_questions_are_safety_relevant(question: str) -> None:
    assert tier_rules().classify(question).tier is Tier.SAFETY_RELEVANT


def test_admin_question_is_routine() -> None:
    assert tier_rules().classify("Who owns PR-CORP-001?").tier is Tier.ROUTINE


def test_rules_report_which_rule_matched() -> None:
    assert tier_rules().classify("How do I purge the main?").matched == ("purging-commissioning",)


def test_stricter_tier_wins_either_way_round() -> None:
    assert stricter(Tier.ROUTINE, Tier.SAFETY_CRITICAL) is Tier.SAFETY_CRITICAL
    assert stricter(Tier.SAFETY_CRITICAL, Tier.ROUTINE) is Tier.SAFETY_CRITICAL


def test_equal_tiers_stay_the_same() -> None:
    assert stricter(Tier.SAFETY_RELEVANT, Tier.SAFETY_RELEVANT) is Tier.SAFETY_RELEVANT


EMERGENCY_CASES = [
    case
    for suite in ("golden", "redteam")
    for case in load_cases(Path(f"evals/{suite}.yaml"))
    if case.behaviour == "emergency"
]
# Questions about procedures, not reports of danger. (A question relaying a customer's report of
# a gas smell does get the card, which is the right answer to it.)
PROCEDURE_QUESTIONS = [
    "Which procedure covers a reported gas smell at a meter?",
    "What do I do if a digger hits a gas main?",
    "How do we protect services from being hit by excavators?",
    "Why is the meter not moving?",
    "Is gas blowing from the vent stack normal during a purge?",
    "Has the inspection backlog caught up?",
    "What PPE do I need where there is a sparking risk?",
    "Which procedure covers overhead line clearances?",
    "What happens if someone had a shock last year, do we report it to HSE?",
    "How often is the cable inspected?",
]


@pytest.mark.parametrize("case", EMERGENCY_CASES, ids=lambda case: case.id)
def test_every_emergency_case_is_caught_without_any_model(case: Case) -> None:
    """The emergency card must not depend on a model, which can be down. Rules see the question
    after personal data is masked, as in the assistant."""
    question = pii_masker().mask(case.question).text

    assert tier_rules().classify(question).tier is Tier.EMERGENCY


@pytest.mark.parametrize("question", PROCEDURE_QUESTIONS)
def test_question_about_an_emergency_procedure_is_not_an_emergency(question: str) -> None:
    assert tier_rules().classify(question).tier is not Tier.EMERGENCY
