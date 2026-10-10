"""Mask personal data before the question reaches a model, the logs or the audit trail."""

import re
from dataclasses import dataclass
from functools import cache

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import PhoneRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from gigawhat.retrieval.query import ASSET_ID, DOC_ID

SPACY_MODEL = "en_core_web_md"
# Presidio scores UK phone numbers at 0.4; a higher threshold would let them through.
MIN_SCORE = 0.35
CASE_SENSITIVE = re.DOTALL | re.MULTILINE

PLACEHOLDERS = {
    "PERSON": "[name]",
    "PHONE_NUMBER": "[phone]",
    "EMAIL_ADDRESS": "[email]",
    "STREET_ADDRESS": "[address]",
    "UK_POSTCODE": "[postcode]",
    "UK_NHS": "[NHS number]",
    "CREDIT_CARD": "[card number]",
    "IBAN_CODE": "[bank account]",
    "IP_ADDRESS": "[IP address]",
}

STREET_TYPES = "Road|Street|Lane|Avenue|Close|Way|Drive|Crescent|Gardens|Place|Terrace|Court|Grove"
HOUSE_AND_STREET = (
    rf"(?<![-\w])\d{{1,4}}[A-Za-z]?,?\s+(?:[A-Z][a-z]+\s){{1,2}}(?:{STREET_TYPES})\b"
    rf"|\b(?:number|no\.?)\s+\d{{1,4}}\s+(?:[A-Z][a-z]+\s){{1,2}}(?:{STREET_TYPES})\b"
)
UK_POSTCODE = r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b"
# Backstop for numbers the phone library rejects as unallocated, which are still personal data.
UK_PHONE = r"(?<![\d-])(?:\+44\s?\(?0?\)?\s?|0)\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}(?![\d-])"

# Company vocabulary that NER can mistake for names: sites, places and job titles. Only spans
# without digits are excused, so an address with a house number is always masked.
COMPANY_TERMS = (
    "Harrowmere|Kingsmead|Ashford|Brookfield|Orchard Way|Riverside|Mill Lane|Station Road|"
    "Vale|Authorised Person|Competent Person|Control Engineer|Gas Network Controller|"
    "First Call Operative|Safety Manager|Document controller"
)
IDENTIFIER = re.compile(f"{ASSET_ID.pattern}|{DOC_ID.pattern}", re.IGNORECASE)
ALLOWED = [
    rf"(?i)^(?!.*\d)(?=.*\b(?:{COMPANY_TERMS})\b).*$",
    r"^0800 111 999$",
]


@dataclass(frozen=True)
class MaskedText:
    text: str
    entities: tuple[str, ...]


class PiiMasker:
    def __init__(self) -> None:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
            }
        )
        nlp_engine = provider.create_engine()
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)
        registry.remove_recognizer("PhoneRecognizer")
        registry.add_recognizer(PhoneRecognizer(supported_regions=("GB",)))
        registry.add_recognizer(_pattern("STREET_ADDRESS", HOUSE_AND_STREET))
        registry.add_recognizer(_pattern("UK_POSTCODE", UK_POSTCODE))
        registry.add_recognizer(_pattern("PHONE_NUMBER", UK_PHONE))
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
        self._anonymizer = AnonymizerEngine()

    def mask(self, text: str) -> MaskedText:
        findings = self._analyze(text)
        operators = {
            entity: OperatorConfig("replace", {"new_value": placeholder})
            for entity, placeholder in PLACEHOLDERS.items()
        }
        masked = self._anonymizer.anonymize(
            text=text,
            analyzer_results=findings,  # type: ignore[arg-type]
            operators=operators,
        )
        return MaskedText(masked.text, tuple(sorted({f.entity_type for f in findings})))

    def find(self, text: str) -> list[str]:
        """The personal data found in the text, as written. Used to check nothing leaks."""
        return [text[finding.start : finding.end] for finding in self._analyze(text)]

    def _analyze(self, text: str) -> list[RecognizerResult]:
        findings = self._analyzer.analyze(
            text=text,
            language="en",
            entities=list(PLACEHOLDERS),
            score_threshold=MIN_SCORE,
            allow_list=ALLOWED,
            allow_list_match="regex",
            regex_flags=CASE_SENSITIVE,
        )
        identifiers = [m.span() for m in IDENTIFIER.finditer(text)]
        return [f for f in findings if not _overlaps_any(f, identifiers)]


@cache
def pii_masker() -> PiiMasker:
    return PiiMasker()


def _pattern(entity: str, regex: str) -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity=entity,
        patterns=[Pattern(entity.lower(), regex, 0.7)],
        global_regex_flags=CASE_SENSITIVE,
    )


def _overlaps_any(finding: RecognizerResult, spans: list[tuple[int, int]]) -> bool:
    """Asset and document IDs (FDR-ASH-07, PR-GAS-031) are never personal data."""
    return any(finding.start < end and start < finding.end for start, end in spans)
