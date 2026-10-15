from pathlib import Path

import pytest

from gigawhat.ingestion.chunking import (
    CHUNK_MAX_TOKENS,
    CHUNK_TOKENIZER,
    DoclingChunker,
    SectionChunk,
)

pytestmark = pytest.mark.slow

SAMPLE = Path(__file__).parent / "fixtures" / "sample_procedure.md"
PUBLISHED = Path(__file__).parent.parent / "data/corpus/procedures/gas/PR-GAS-010_v4.pdf"


@pytest.fixture(scope="module")
def sections() -> list[SectionChunk]:
    return DoclingChunker(CHUNK_TOKENIZER, CHUNK_MAX_TOKENS).split(SAMPLE)


def section_titled(sections: list[SectionChunk], title: str) -> SectionChunk:
    [match] = [section for section in sections if section.headings[-1] == title]
    return match


def test_each_procedure_subsection_is_one_chunk(sections: list[SectionChunk]) -> None:
    titles = [section.headings[-1] for section in sections]

    assert titles.count("6.2 Vent stack") == 1


def test_warning_stays_with_the_steps_it_governs(sections: list[SectionChunk]) -> None:
    vent_stack = section_titled(sections, "6.2 Vent stack")

    assert "WARNING: Vented gas can drift" in vent_stack.body
    assert "6.2.1 Erect the vent stack" in vent_stack.body


def test_hold_point_stays_with_its_step(sections: list[SectionChunk]) -> None:
    purge = section_titled(sections, "6.3 Purge to gas")

    assert purge.body.startswith("HOLD POINT:")
    assert "6.3.1 Open the inlet valve" in purge.body


def test_headings_trail_down_from_the_document_title(sections: list[SectionChunk]) -> None:
    isolation = section_titled(sections, "6.1 Isolation")

    assert isolation.headings == ("PR-GAS-099 Purging Test Mains", "6 Procedure", "6.1 Isolation")


@pytest.fixture(scope="module")
def published_sections() -> list[SectionChunk]:
    return DoclingChunker(CHUNK_TOKENIZER, CHUNK_MAX_TOKENS).split(PUBLISHED)


def test_published_pdf_has_the_same_sections_as_its_source(
    published_sections: list[SectionChunk],
) -> None:
    source = DoclingChunker(CHUNK_TOKENIZER, CHUNK_MAX_TOKENS).split(PUBLISHED.with_suffix(".md"))

    assert {s.headings[-1] for s in published_sections} == {s.headings[-1] for s in source}


def test_published_pdf_keeps_a_hold_point_with_its_steps(
    published_sections: list[SectionChunk],
) -> None:
    planning = section_titled(published_sections, "6.2 Planning and authorisation")

    assert "HOLD POINT: Do not operate any valve" in planning.body
