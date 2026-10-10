"""Example questions per persona, chosen to show each kind of behaviour."""

from gigawhat.personas import Persona

STARTERS: dict[Persona, list[tuple[str, str]]] = {
    Persona.GAS_FIELD_ENGINEER: [
        ("Purge a PE main", "How do I purge the 75 mbar main on Mill Lane before gas-in?"),
        ("G-112 history", "What have the last inspections and alarms on G-112 shown?"),
        ("What changed?", "What changed in PR-GAS-031 v3 and why?"),
        ("Gas smell", "A resident at 14 Station Road says she can smell gas in her kitchen"),
    ],
    Persona.ELECTRICITY_CONTROL_ROOM: [
        (
            "T-104 acetylene",
            "Summarise the acetylene trend on T-104 and what PR-ELEC-044 says to do",
        ),
        ("Isolate a feeder", "How do I isolate and earth the 11 kV feeder FDR-ASH-07?"),
        ("Switching alone", "Can HV switching be done by one person on their own?"),
        ("Inspection rules", "How often must Ashford Road primary substation be inspected?"),
    ],
    Persona.GAS_AUTHORISED_PERSON: [
        ("Permit checks", "What must be in place before a gas permit-to-work is issued?"),
        ("SSV-112 trip", "Why did SSV-112 trip in March and what was done about it?"),
    ],
    Persona.ELECTRICITY_AUTHORISED_PERSON: [
        ("Hold points", "What hold points are in PR-ELEC-012?"),
        ("Tunnel entry", "What gas readings stop an entry to the Kingsmead cable tunnel?"),
    ],
    Persona.DOCUMENT_CONTROLLER: [
        ("Draft procedure", "What does the live working procedure PR-ELEC-070 say?"),
        ("Current version", "Which version of PR-ELEC-012 is current and what changed from v3?"),
    ],
    Persona.AUDITOR: [
        ("Incidents", "Summarise the incidents involving G-112 and their root causes"),
        ("HSE guidance", "What does HSE guidance say a permit-to-work system should cover?"),
    ],
}
