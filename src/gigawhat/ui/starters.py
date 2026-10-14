"""Example questions per persona, chosen to show each kind of behaviour."""

from dataclasses import dataclass

from gigawhat.identity.personas import Persona


@dataclass(frozen=True)
class Example:
    label: str
    question: str
    # A Lucide icon in public/icons/. Red marks the emergency example; the rest are teal.
    icon: str

    @property
    def icon_url(self) -> str:
        return f"/public/icons/{self.icon}.svg"


STARTERS: dict[Persona, list[Example]] = {
    Persona.GAS_FIELD_ENGINEER: [
        Example(
            "Purge a PE main", "How do I purge the 75 mbar main on Mill Lane before gas-in?", "wind"
        ),
        Example(
            "G-112 history", "What have the last inspections and alarms on G-112 shown?", "history"
        ),
        Example("What changed?", "What changed in PR-GAS-031 v3 and why?", "git-compare"),
        Example(
            "Gas smell",
            "A resident at 14 Station Road says she can smell gas in her kitchen",
            "siren",
        ),
    ],
    Persona.ELECTRICITY_CONTROL_ROOM: [
        Example(
            "T-104 acetylene",
            "Summarise the acetylene trend on T-104 and what PR-ELEC-044 says to do",
            "trending-up",
        ),
        Example(
            "Isolate a feeder", "How do I isolate and earth the 11 kV feeder FDR-ASH-07?", "unplug"
        ),
        Example("Switching alone", "Can HV switching be done by one person on their own?", "users"),
        Example(
            "Inspection rules",
            "How often must Ashford Road primary substation be inspected?",
            "calendar-check",
        ),
    ],
    Persona.GAS_AUTHORISED_PERSON: [
        Example(
            "Permit checks",
            "What must be in place before a gas permit-to-work is issued?",
            "clipboard-check",
        ),
        Example(
            "SSV-112 trip",
            "Why did SSV-112 trip in March and what was done about it?",
            "triangle-alert",
        ),
    ],
    Persona.ELECTRICITY_AUTHORISED_PERSON: [
        Example("Hold points", "What hold points are in PR-ELEC-012?", "hand"),
        Example(
            "Tunnel entry",
            "What gas readings stop an entry to the Kingsmead cable tunnel?",
            "door-open",
        ),
    ],
    Persona.DOCUMENT_CONTROLLER: [
        Example(
            "Draft procedure",
            "What does the live working procedure PR-ELEC-070 say?",
            "file-pen-line",
        ),
        Example(
            "Current version",
            "Which version of PR-ELEC-012 is current and what changed from v3?",
            "file-check",
        ),
    ],
    Persona.AUDITOR: [
        Example(
            "Incidents",
            "Summarise the incidents involving G-112 and their root causes",
            "triangle-alert",
        ),
        Example(
            "HSE guidance",
            "What does HSE guidance say a permit-to-work system should cover?",
            "book-open",
        ),
    ],
}
