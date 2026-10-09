from typing import Any

import pytest
from pydantic import ValidationError

from gigawhat.config import Settings
from gigawhat.corpus.register import DocumentEntry, DocumentStatus, Register, load_register


def version(number: int, status: str, **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "version": number,
        "status": status,
        "effective_from": "2026-01-05",
        "review_due": "2029-01-05",
        "approver": "Gas Safety Manager",
        "safety_critical": True,
        "sites": [],
        "asset_classes": [],
        "file": f"procedures/gas/PR-GAS-099_v{number}.md",
    }
    return entry | overrides


def document(*versions: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "doc_id": "PR-GAS-099",
        "title": "Test procedure",
        "business_unit": "gas",
        "doc_type": "procedure",
        "owner": "Head of Gas Network Operations",
        "versions": list(versions),
    }
    return entry | overrides


def test_project_register_is_valid() -> None:
    register = load_register(Settings(_env_file=None).register_path)

    assert len(register.documents) > 0


def test_project_register_has_one_current_version_of_each_procedure() -> None:
    register = load_register(Settings(_env_file=None).register_path)

    for entry in register.documents:
        approved = [v for v in entry.versions if v.status is DocumentStatus.APPROVED]
        assert len(approved) <= 1, entry.doc_id


def test_accepts_superseded_then_approved() -> None:
    entry = DocumentEntry.model_validate(document(version(1, "superseded"), version(2, "approved")))

    assert [v.status for v in entry.versions] == [
        DocumentStatus.SUPERSEDED,
        DocumentStatus.APPROVED,
    ]


def test_rejects_two_approved_versions() -> None:
    with pytest.raises(ValidationError, match="only one version can be approved"):
        DocumentEntry.model_validate(document(version(1, "approved"), version(2, "approved")))


def test_rejects_superseded_version_newer_than_approved() -> None:
    with pytest.raises(ValidationError, match="superseded version is newer"):
        DocumentEntry.model_validate(document(version(1, "approved"), version(2, "superseded")))


def test_rejects_repeated_version_number() -> None:
    with pytest.raises(ValidationError, match="version numbers must be unique"):
        DocumentEntry.model_validate(document(version(1, "superseded"), version(1, "approved")))


def test_rejects_approved_procedure_without_effective_date() -> None:
    with pytest.raises(ValidationError, match="need an effective_from date"):
        DocumentEntry.model_validate(document(version(1, "approved", effective_from=None)))


def test_allows_approved_guidance_without_effective_date() -> None:
    entry = DocumentEntry.model_validate(
        document(version(1, "approved", effective_from=None), doc_type="guidance")
    )

    assert entry.versions[0].effective_from is None


def test_rejects_document_with_no_versions() -> None:
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(document())


def test_rejects_malformed_doc_id() -> None:
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(document(version(1, "approved"), doc_id="GAS 99"))


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(document(version(1, "approved"), colour="red"))


def test_rejects_duplicate_doc_ids() -> None:
    entry = document(version(1, "approved"))

    with pytest.raises(ValidationError, match="duplicate doc_id: PR-GAS-099"):
        Register.model_validate({"documents": [entry, entry]})
