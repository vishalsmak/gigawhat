"""Download public HSE guidance named in the register. The PDFs are fetched, not redistributed."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx

from gigawhat.corpus.register import Register

PDF_MAGIC = b"%PDF"


class NotAPdfError(Exception):
    pass


class ChecksumMismatchError(Exception):
    """The download isn't the file the register vouches for."""


@dataclass(frozen=True)
class GuidanceFile:
    doc_id: str
    path: Path
    downloaded: bool


def fetch_guidance(register: Register, corpus_dir: Path, http: httpx.Client) -> list[GuidanceFile]:
    """Download each guidance document that isn't already on disk."""
    results: list[GuidanceFile] = []
    for document in register.documents:
        if document.source_url is None:
            continue
        target = (corpus_dir / document.versions[-1].file).resolve()
        if target.exists():
            results.append(GuidanceFile(document.doc_id, target, downloaded=False))
            continue
        _download_pdf(http, document.source_url, target, document.source_sha256)
        results.append(GuidanceFile(document.doc_id, target, downloaded=True))
    return results


def _download_pdf(http: httpx.Client, url: str, target: Path, expected_sha256: str | None) -> None:
    response = http.get(url, follow_redirects=True)
    response.raise_for_status()
    if not response.content.startswith(PDF_MAGIC):
        raise NotAPdfError(f"{url} did not return a PDF")
    digest = hashlib.sha256(response.content).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ChecksumMismatchError(
            f"{url} has changed since it was registered (sha256 {digest}). Review the new "
            "edition, then update source_sha256 in the register."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_bytes(response.content)
    partial.rename(target)
