# /// script
# requires-python = ">=3.12"
# dependencies = ["markdown-it-py>=3", "playwright>=1.47", "pypdf>=5", "pyyaml>=6"]
# ///
"""Publish the fictional procedures as PDFs, the way a document management system would.

The Markdown files are the editable source; the register points ingestion at the PDFs. Each PDF
records the SHA-256 of its Markdown source in its metadata, so `tests/test_project_data.py`
fails when a source is edited and its PDF is not published again.

    uv run scripts/render_procedures.py           # publish new or changed procedures
    uv run scripts/render_procedures.py --force   # publish every procedure again

PDFs are printed with the installed Google Chrome through Playwright. Without Chrome, run
`uvx playwright install chromium` and pass `--channel chromium`.
"""

import argparse
import hashlib
import html
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt
from playwright.sync_api import Page, sync_playwright
from pypdf import PdfReader, PdfWriter

CORPUS = Path(__file__).resolve().parent.parent / "data" / "corpus"
SOURCE_KEY = "source-sha256:"
DIVISIONS = {"gas": "GigaWhat Gas", "electricity": "GigaWhat Electricity"}
# Paragraphs that open with these labels are printed as boxes, as in the companies' templates.
CALLOUTS = {"WARNING": "warning", "CAUTION": "caution", "HOLD POINT": "hold", "NOTE": "note"}
CALLOUT = re.compile(r"<p>(" + "|".join(CALLOUTS) + r"):")

STYLE = """
@page { size: A4; margin: 24mm 18mm 22mm 18mm; }
body { margin: 0; font: 10.5pt/1.45 "Helvetica Neue", Arial, sans-serif; color: #1b1f24; }
img.artwork { display: block; width: 174mm; margin: 0 0 12pt; }
h1 { font-size: 18pt; color: #0b2545; margin: 0 0 10pt; }
h2 { font-size: 13pt; color: #0b2545; margin: 16pt 0 6pt; padding-bottom: 2pt;
  border-bottom: 1px solid #c9d1da; break-after: avoid; }
h3 { font-size: 11pt; color: #0b2545; margin: 12pt 0 4pt; break-after: avoid; }
p, li { margin: 0 0 6pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 12pt; font-size: 9.5pt;
  break-inside: avoid; }
th, td { border: 1px solid #b9c2cc; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: #eef2f6; }
.callout { border-left: 4pt solid; padding: 6pt 9pt; margin: 8pt 0; break-inside: avoid; }
.warning { border-color: #b03a2e; background: #fbeceb; }
.caution { border-color: #b9770e; background: #fdf3e3; }
.hold { border-color: #7d3c98; background: #f4ecf7; }
.note { border-color: #2471a3; background: #eaf2f8; }
"""
# The letterhead and status banner are drawn on canvases and placed as PNG images, the way a logo
# sits in a real template. As text, the PDF parser read them as headings and body text. Headless
# Chrome prints canvases blank, hence the images. Each page header still names the status in text.
ARTWORK_SCRIPT = """
const SCALE = 3;
// The printable column of an A4 page with 18 mm side margins: 174 mm at 96 pixels an inch.
const COLUMN_WIDTH = 658;
const FONT = "'Helvetica Neue', Arial, sans-serif";
function prepare(canvas, height) {
  const width = COLUMN_WIDTH;
  canvas.style.height = height + "px";
  canvas.width = width * SCALE;
  canvas.height = height * SCALE;
  const context = canvas.getContext("2d");
  context.scale(SCALE, SCALE);
  return [context, width];
}
function placeAsImage(canvas, height) {
  const image = document.createElement("img");
  image.className = "artwork";
  image.alt = "";
  image.style.height = height + "px";
  image.src = canvas.toDataURL("image/png");
  canvas.replaceWith(image);
}
function wrap(context, text, maxWidth) {
  const lines = [];
  let line = "";
  for (const word of text.split(" ")) {
    const candidate = line ? line + " " + word : word;
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  return line ? [...lines, line] : lines;
}
// A title on one line: the parser reads a wrapped title's second line as a heading of its own.
const title = document.querySelector("h1");
title.style.whiteSpace = "nowrap";
title.style.display = "inline-block";
for (let size = 18; title.offsetWidth > COLUMN_WIDTH && size > 11; size -= 0.5) {
  title.style.fontSize = size - 0.5 + "pt";
}
for (const canvas of document.querySelectorAll("canvas.letterhead")) {
  const [context, width] = prepare(canvas, 48);
  context.fillStyle = "#0b2545";
  context.font = "700 22px " + FONT;
  context.fillText("GigaWhat Energy", 0, 30);
  context.fillStyle = "#4a5560";
  context.font = "12px " + FONT;
  context.textAlign = "right";
  context.fillText(canvas.dataset.division, width, 15);
  context.fillText("Controlled procedure", width, 31);
  context.fillStyle = "#0f7b7b";
  context.fillRect(0, 42, width, 3);
  placeAsImage(canvas, 48);
}
for (const canvas of document.querySelectorAll("canvas.banner")) {
  const font = "700 13px " + FONT;
  const probe = document.createElement("canvas").getContext("2d");
  probe.font = font;
  const width = COLUMN_WIDTH;
  const lines = wrap(probe, canvas.dataset.text.toUpperCase(), width - 28);
  const [context] = prepare(canvas, lines.length * 18 + 18);
  context.strokeStyle = "#b03a2e";
  context.lineWidth = 2;
  context.strokeRect(1, 1, width - 2, lines.length * 18 + 16);
  context.fillStyle = "#b03a2e";
  context.font = font;
  lines.forEach((line, index) => context.fillText(line, 14, 22 + index * 18));
  placeAsImage(canvas, lines.length * 18 + 18);
}
"""
MARGIN_TEXT = "font: 7.5pt Arial, sans-serif; color: #5b6670; width: 100%; padding: 0 18mm;"


@dataclass(frozen=True)
class Publication:
    doc_id: str
    title: str
    version: int
    status: str
    division: str
    pdf: Path
    banner: str | None

    @property
    def source(self) -> Path:
        return self.pdf.with_suffix(".md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="publish every procedure again")
    parser.add_argument("--channel", default="chrome", help="Playwright browser channel")
    arguments = parser.parse_args()

    publications = list(registered_procedures(CORPUS / "register.yaml"))
    stale = [p for p in publications if arguments.force or not is_current(p)]
    if not stale:
        print(f"All {len(publications)} procedure PDFs are current.")
        return
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=arguments.channel)
        for publication in stale:
            # A fresh page each time: on a reused page the artwork came out blank.
            page = browser.new_page()
            publish(page, publication)
            page.close()
            print(f"published {publication.pdf.relative_to(CORPUS)}")
        browser.close()


def registered_procedures(register_path: Path) -> list[Publication]:
    register = yaml.safe_load(register_path.read_text())
    publications = []
    for document in register["documents"]:
        if document["doc_type"] != "procedure":
            continue
        versions = document["versions"]
        for index, version in enumerate(versions):
            later = versions[index + 1] if index + 1 < len(versions) else None
            publications.append(
                Publication(
                    doc_id=document["doc_id"],
                    title=document["title"],
                    version=version["version"],
                    status=version["status"],
                    division=DIVISIONS.get(document["business_unit"], "GigaWhat Energy"),
                    pdf=(register_path.parent / version["file"]).resolve().with_suffix(".pdf"),
                    banner=status_banner(version["status"], later),
                )
            )
    return publications


def status_banner(status: str, later: dict[str, Any] | None) -> str | None:
    """What a reader must see first on a version that is not approved for use."""
    if status == "superseded" and later:
        return (
            f"Superseded by version {later['version']} from {later['effective_from']}. "
            "Do not use: check the document register for the current version."
        )
    if status == "draft":
        return "Draft: not approved for use."
    if status == "withdrawn":
        return "Withdrawn: do not use. Check the document register."
    return None


def source_digest(publication: Publication) -> str:
    return hashlib.sha256(publication.source.read_bytes()).hexdigest()


def is_current(publication: Publication) -> bool:
    if not publication.pdf.exists():
        return False
    keywords: str = PdfReader(publication.pdf).metadata.get("/Keywords", "")
    return keywords == SOURCE_KEY + source_digest(publication)


def publish(page: Page, publication: Publication) -> None:
    page.set_content(document_html(publication), wait_until="load")
    page.wait_for_function("[...document.images].every((image) => image.complete)")
    printed = page.pdf(
        format="A4",
        print_background=True,
        display_header_footer=True,
        header_template=margin_html(
            f"GigaWhat Energy · {publication.doc_id} v{publication.version} · "
            f"{html.escape(publication.title)}",
            publication.status.upper(),
        ),
        footer_template=margin_html(
            "Uncontrolled when printed. Fictional document for the GigaWhat demo.",
            'Page <span class="pageNumber"></span> of <span class="totalPages"></span>',
        ),
        margin={"top": "24mm", "bottom": "22mm", "left": "18mm", "right": "18mm"},
    )
    write_with_metadata(printed, publication)


def document_html(publication: Publication) -> str:
    body = MarkdownIt("commonmark").enable("table").render(publication.source.read_text())
    body = CALLOUT.sub(lambda m: f'<p class="callout {CALLOUTS[m.group(1)]}">{m.group(1)}:', body)
    banner = (
        f'<canvas class="banner" data-text="{html.escape(publication.banner)}"></canvas>'
        if publication.banner
        else ""
    )
    # The banner goes straight after the title, so it is the first thing read.
    body = body.replace("</h1>", f"</h1>{banner}", 1)
    letterhead = f'<canvas class="letterhead" data-division="{publication.division}"></canvas>'
    title = f"{publication.doc_id} v{publication.version} {html.escape(publication.title)}"
    return (
        f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>{title}</title>'
        f"<style>{STYLE}</style></head><body>{letterhead}{body}"
        f"<script>{ARTWORK_SCRIPT}</script></body></html>"
    )


def margin_html(left: str, right: str) -> str:
    return (
        f'<div style="{MARGIN_TEXT} display: flex; justify-content: space-between;">'
        f"<span>{left}</span><span>{right}</span></div>"
    )


def write_with_metadata(printed: bytes, publication: Publication) -> None:
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(printed)))
    writer.add_metadata(
        {
            "/Title": f"{publication.doc_id} v{publication.version} {publication.title}",
            "/Author": "GigaWhat Energy (fictional)",
            "/Subject": f"Controlled procedure, {publication.status}",
            "/Keywords": SOURCE_KEY + source_digest(publication),
            "/Creator": "scripts/render_procedures.py",
        }
    )
    with publication.pdf.open("wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
