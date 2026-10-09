from dataclasses import replace
from datetime import date

from gigawhat.corpus.catalogue import StoredVersion

TODAY = date(2026, 10, 9)
STORED = StoredVersion(
    doc_id="PR-ELEC-052",
    title="Routine Substation Inspection",
    business_unit="electricity",
    version=4,
    status="approved",
    effective_from=date(2024, 3, 4),
    review_due=TODAY,
    safety_critical=False,
    chunk_count=9,
)


def test_review_due_today_is_not_overdue() -> None:
    assert not STORED.review_overdue(TODAY)


def test_review_due_yesterday_is_overdue() -> None:
    assert replace(STORED, review_due=date(2026, 10, 8)).review_overdue(TODAY)


def test_no_review_date_is_never_overdue() -> None:
    assert not replace(STORED, review_due=None).review_overdue(TODAY)
