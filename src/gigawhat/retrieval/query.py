"""Find the precise terms in a question: document IDs, asset IDs, abbreviations and ratings."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from importlib import resources

import yaml

DOC_ID = re.compile(r"\b(?:PR-(?:ELEC|GAS|CORP)-\d{3}|HSE-(?:HSG|HSR|L)\d+)\b", re.IGNORECASE)
ASSET_ID = re.compile(
    r"\b(?:GT-\d|T-\d{3}|TX-[A-Z]{3}-\d{2}|RMU-[A-Z]{3}-\d{2}|SWG-[A-Z]{3}-\d{2}|FDR-[A-Z]{3}-\d{2}"
    r"|BAT-[A-Z]{3}|CT-[A-Z]{3}-\d{2}|PRS-[A-Z]{3}-\d{2}|SSV-(?:\d{3}|[A-Z]{3}-[AB])"
    r"|FLT-(?:\d{3}|[A-Z]{3}-\d{2})|G-\d{3}|MAIN-(?:IP|MP|LP)-\d{2})\b",
    re.IGNORECASE,
)
RATING = re.compile(r"\b\d+(?:\.\d+)?\s?(?:kV|mbar|bar|MVA|ppm|mg/m3)\b", re.IGNORECASE)
WORD = re.compile(r"\b[A-Z]{2,6}\b")


@dataclass(frozen=True)
class QueryAnalysis:
    question: str
    doc_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    expansions: tuple[str, ...]
    ratings: tuple[str, ...]

    @property
    def keyword_query(self) -> str:
        """The single most specific term for keyword search.

        langchain-postgres joins keyword-search words with AND, so one precise term finds exact
        matches where a whole sentence would usually find nothing.
        """
        for terms in (self.asset_ids, self.expansions, self.ratings):
            if terms:
                return terms[0]
        return ""


@cache
def abbreviations() -> dict[str, str]:
    source = resources.files("gigawhat.retrieval").joinpath("glossary.yaml").read_text()
    glossary: dict[str, str] = yaml.safe_load(source)["abbreviations"]
    return glossary


def analyse_query(question: str) -> QueryAnalysis:
    glossary = abbreviations()
    return QueryAnalysis(
        question=question,
        doc_ids=_unique(match.upper() for match in DOC_ID.findall(question)),
        asset_ids=_unique(match.upper() for match in ASSET_ID.findall(question)),
        expansions=_unique(glossary[word] for word in WORD.findall(question) if word in glossary),
        ratings=_unique(RATING.findall(question)),
    )


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))
