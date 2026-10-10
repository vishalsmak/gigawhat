"""Demo personas. Each maps to the role and business-unit access a real user would get from SSO."""

from dataclasses import dataclass
from enum import StrEnum

from gigawhat.corpus.register import BusinessUnit


class Persona(StrEnum):
    GAS_FIELD_ENGINEER = "gas_field_engineer"
    ELECTRICITY_CONTROL_ROOM = "electricity_control_room"
    GAS_AUTHORISED_PERSON = "gas_authorised_person"
    ELECTRICITY_AUTHORISED_PERSON = "electricity_authorised_person"
    DOCUMENT_CONTROLLER = "document_controller"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class PersonaProfile:
    persona: Persona
    title: str
    role: str
    business_units: tuple[BusinessUnit, ...]
    releases_for: BusinessUnit | None
    sees_drafts: bool
    description: str

    @property
    def can_release(self) -> bool:
        return self.releases_for is not None


GAS_AND_SHARED = (BusinessUnit.GAS, BusinessUnit.SHARED)
ELECTRICITY_AND_SHARED = (BusinessUnit.ELECTRICITY, BusinessUnit.SHARED)
ALL_UNITS = (BusinessUnit.GAS, BusinessUnit.ELECTRICITY, BusinessUnit.SHARED)

PROFILES = {
    profile.persona: profile
    for profile in (
        PersonaProfile(
            Persona.GAS_FIELD_ENGINEER,
            "Gas field engineer",
            "First Call Operative",
            GAS_AND_SHARED,
            None,
            False,
            "Responds to escapes and works on governors and mains. Sees gas and company-wide "
            "documents and records.",
        ),
        PersonaProfile(
            Persona.ELECTRICITY_CONTROL_ROOM,
            "Electricity control room",
            "Control Engineer",
            ELECTRICITY_AND_SHARED,
            None,
            False,
            "Runs the 132/33/11 kV network. Sees electricity and company-wide documents "
            "and records.",
        ),
        PersonaProfile(
            Persona.GAS_AUTHORISED_PERSON,
            "Authorised Person (Gas)",
            "Authorised Person (Gas)",
            GAS_AND_SHARED,
            BusinessUnit.GAS,
            False,
            "Releases or declines safety-critical gas answers that colleagues have requested.",
        ),
        PersonaProfile(
            Persona.ELECTRICITY_AUTHORISED_PERSON,
            "Authorised Person (HV)",
            "Authorised Person (HV)",
            ELECTRICITY_AND_SHARED,
            BusinessUnit.ELECTRICITY,
            False,
            "Releases or declines safety-critical electricity answers that colleagues have "
            "requested.",
        ),
        PersonaProfile(
            Persona.DOCUMENT_CONTROLLER,
            "Document controller",
            "Document controller",
            ALL_UNITS,
            None,
            True,
            "Maintains the document register. Sees every unit, including drafts.",
        ),
        PersonaProfile(
            Persona.AUDITOR,
            "Auditor",
            "Auditor",
            ALL_UNITS,
            None,
            False,
            "Reviews the audit trail of questions, sources, answers and approvals. Read-only.",
        ),
    )
}


def profile_of(persona: Persona) -> PersonaProfile:
    return PROFILES[persona]
