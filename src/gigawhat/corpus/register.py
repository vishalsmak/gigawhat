"""The document register: which documents exist, which version is current, and who they apply to.

The register is the source of truth for document control. A file's own contents never decide
whether it is current.
"""

from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

DOC_ID_PATTERN = r"^(PR-(ELEC|GAS|CORP)|HSE-[A-Z]+)-?\d+$"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class BusinessUnit(StrEnum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    SHARED = "shared"


class DocType(StrEnum):
    PROCEDURE = "procedure"
    GUIDANCE = "guidance"


class VersionEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: PositiveInt
    status: DocumentStatus
    effective_from: date | None
    review_due: date | None
    approver: str | None
    safety_critical: bool
    sites: tuple[str, ...]
    asset_classes: tuple[str, ...]
    file: str


class DocumentEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_id: str = Field(pattern=DOC_ID_PATTERN)
    title: str
    business_unit: BusinessUnit
    doc_type: DocType
    owner: str
    source_url: str | None = None
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    versions: tuple[VersionEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_document_control(self) -> Self:
        numbers = [entry.version for entry in self.versions]
        if len(numbers) != len(set(numbers)):
            raise ValueError(f"{self.doc_id}: version numbers must be unique")
        approved = [entry for entry in self.versions if entry.status is DocumentStatus.APPROVED]
        if len(approved) > 1:
            raise ValueError(f"{self.doc_id}: only one version can be approved")
        if approved:
            self._check_approved_version(approved[0])
        return self

    def _check_approved_version(self, approved: VersionEntry) -> None:
        superseded = [e for e in self.versions if e.status is DocumentStatus.SUPERSEDED]
        if any(entry.version > approved.version for entry in superseded):
            raise ValueError(
                f"{self.doc_id}: a superseded version is newer than v{approved.version}"
            )
        if self.doc_type is DocType.PROCEDURE and approved.effective_from is None:
            raise ValueError(f"{self.doc_id}: approved procedures need an effective_from date")


class Register(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: tuple[DocumentEntry, ...]

    @model_validator(mode="after")
    def check_unique_ids(self) -> Self:
        ids = [document.doc_id for document in self.documents]
        duplicates = sorted({doc_id for doc_id in ids if ids.count(doc_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate doc_id: {', '.join(duplicates)}")
        return self


def load_register(path: Path) -> Register:
    return Register.model_validate(yaml.safe_load(path.read_text()))
