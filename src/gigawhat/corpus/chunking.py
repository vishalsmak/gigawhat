"""Heading-aware chunking with Docling, through its official LangChain loader."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.doc_chunk import DocChunk
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.document import DoclingDocument
from langchain_docling import DoclingLoader
from langchain_docling.loader import BaseMetaExtractor


@dataclass(frozen=True)
class SectionChunk:
    headings: tuple[str, ...]
    body: str


class Chunker(Protocol):
    def split(self, path: Path) -> list[SectionChunk]: ...


class _SectionMetaExtractor(BaseMetaExtractor):
    """Keeps the raw chunk text and its heading trail; GigaWhat writes its own context header."""

    def extract_chunk_meta(self, file_path: str, chunk: BaseChunk) -> dict[str, Any]:
        doc_chunk = DocChunk.model_validate(chunk)
        return {"headings": list(doc_chunk.meta.headings or []), "body": doc_chunk.text}

    def extract_dl_doc_meta(self, file_path: str, dl_doc: DoclingDocument) -> dict[str, Any]:
        return {}


class DoclingChunker:
    def __init__(self, tokenizer_name: str, max_tokens: int) -> None:
        tokenizer = HuggingFaceTokenizer.from_pretrained(
            model_name=tokenizer_name, max_tokens=max_tokens
        )
        self._chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)
        # Our sources are born-digital. OCR would add nothing and fetches extra models at run time.
        pdf_options = PdfPipelineOptions(do_ocr=False)
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
        )

    def split(self, path: Path) -> list[SectionChunk]:
        loader = DoclingLoader(
            file_path=str(path),
            converter=self._converter,
            chunker=self._chunker,
            meta_extractor=_SectionMetaExtractor(),
        )
        return [
            SectionChunk(headings=tuple(chunk.metadata["headings"]), body=chunk.metadata["body"])
            for chunk in loader.lazy_load()
        ]
