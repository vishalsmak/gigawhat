from pathlib import Path

import httpx
import pytest

from gigawhat.corpus.hse import NotAPdfError, fetch_guidance
from gigawhat.corpus.register import Register

PDF_BYTES = b"%PDF-1.7 fake"


def guidance_register() -> Register:
    return Register.model_validate(
        {
            "documents": [
                {
                    "doc_id": "HSE-HSG250",
                    "title": "Guidance on permit-to-work systems",
                    "business_unit": "shared",
                    "doc_type": "guidance",
                    "owner": "Health and Safety Executive",
                    "source_url": "https://example.test/hsg250.pdf",
                    "versions": [
                        {
                            "version": 1,
                            "status": "approved",
                            "effective_from": None,
                            "review_due": None,
                            "approver": None,
                            "safety_critical": True,
                            "sites": [],
                            "asset_classes": [],
                            "file": "../raw/hse/hsg250.pdf",
                        }
                    ],
                }
            ]
        }
    )


def client_returning(body: bytes) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body)))


def test_reports_missing_guidance_as_downloaded(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"

    [result] = fetch_guidance(guidance_register(), corpus_dir, client_returning(PDF_BYTES))

    assert result.downloaded


def test_saves_downloaded_guidance_at_its_register_path(tmp_path: Path) -> None:
    fetch_guidance(guidance_register(), tmp_path / "corpus", client_returning(PDF_BYTES))

    assert (tmp_path / "raw/hse/hsg250.pdf").read_bytes() == PDF_BYTES


def test_skips_guidance_already_on_disk(tmp_path: Path) -> None:
    target = tmp_path / "raw/hse/hsg250.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(PDF_BYTES)

    [result] = fetch_guidance(guidance_register(), tmp_path / "corpus", client_returning(b""))

    assert not result.downloaded


def test_refuses_a_response_that_is_not_a_pdf(tmp_path: Path) -> None:
    with pytest.raises(NotAPdfError):
        fetch_guidance(guidance_register(), tmp_path / "corpus", client_returning(b"<html>"))


def test_refused_response_leaves_no_file(tmp_path: Path) -> None:
    with pytest.raises(NotAPdfError):
        fetch_guidance(guidance_register(), tmp_path / "corpus", client_returning(b"<html>"))

    assert not (tmp_path / "raw/hse/hsg250.pdf").exists()
