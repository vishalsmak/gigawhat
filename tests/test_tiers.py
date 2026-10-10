import pytest

from gigawhat.assistant.tiers import Tier, stricter, tier_rules


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
        "steps to do a stream changeover at Harrowmere PRS",
        "how should we dig near the IP main on Vale Road",
        "can I issue a PTW for the governor myself?",
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
