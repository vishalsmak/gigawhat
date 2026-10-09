from datetime import date

import httpx
import typer
from rich.console import Console
from rich.table import Table

from gigawhat.config import get_settings
from gigawhat.corpus.catalogue import StoredVersion, stored_versions
from gigawhat.corpus.hse import fetch_guidance
from gigawhat.corpus.register import DocumentStatus, load_register
from gigawhat.db import create_db_engine, upgrade_to_head
from gigawhat.doctor import Status, run_checks
from gigawhat.records.load import load_records

HTTP_TIMEOUT_SECONDS = 3.0
DOWNLOAD_TIMEOUT_SECONDS = 120.0
STATUS_MARKS = {Status.OK: "✔", Status.WARN: "!", Status.FAIL: "✘"}
STATUS_STYLES = {
    DocumentStatus.APPROVED: "green",
    DocumentStatus.SUPERSEDED: "yellow",
    DocumentStatus.DRAFT: "cyan",
    DocumentStatus.WITHDRAWN: "red",
}

app = typer.Typer(help="GigaWhat operational assistant.", no_args_is_help=True)
db_app = typer.Typer(help="Database schema.", no_args_is_help=True)
data_app = typer.Typer(help="Documents and records.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(data_app, name="data")
console = Console()


@app.command()
def doctor() -> None:
    """Check that the database, models and tracing are ready for the current profile."""
    settings = get_settings()
    console.print(f"Profile: {settings.profile}")
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as http:
        checks = run_checks(settings, http)
    for check in checks:
        console.print(f"  {STATUS_MARKS[check.status]} {check.name:<9} {check.detail}")
    if any(check.status is Status.FAIL for check in checks):
        raise typer.Exit(code=1)


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply all pending migrations to the current profile's database."""
    settings = get_settings()
    upgrade_to_head(settings)
    console.print(f"{settings.database} is up to date.")


@data_app.command("fetch-hse")
def data_fetch_hse() -> None:
    """Download the public HSE guidance listed in the register."""
    settings = get_settings()
    register = load_register(settings.register_path)
    with httpx.Client(timeout=DOWNLOAD_TIMEOUT_SECONDS) as http:
        for guidance in fetch_guidance(register, settings.corpus_dir, http):
            action = "downloaded" if guidance.downloaded else "already present"
            console.print(f"  {guidance.doc_id:<12} {action}")


@data_app.command("ingest")
def data_ingest(
    only: str | None = typer.Option(None, help="Ingest a single document, e.g. PR-GAS-031."),
    rebuild: bool = typer.Option(
        False, help="Delete stored versions first, e.g. after changing chunking. Development only."
    ),
) -> None:
    """Parse, chunk and embed the register's documents, then apply their statuses."""
    # Imported here: Docling loads PyTorch, which would slow every other command.
    from gigawhat.corpus.pipeline import build_ingestor

    settings = get_settings()
    register = load_register(settings.register_path)
    selected = [d for d in register.documents if only is None or d.doc_id == only]
    if not selected:
        raise typer.BadParameter(f"{only} is not in the register", param_hint="--only")

    ingestor = build_ingestor(settings)
    for document in selected:
        if rebuild:
            ingestor.forget_document(document.doc_id)
        for report in ingestor.ingest_document(document):
            chunks = f"{report.chunk_count} chunks" if report.chunk_count else ""
            console.print(
                f"  {report.doc_id:<12} v{report.version:<3} {report.status:<11}"
                f" {report.outcome:<13} {chunks}"
            )


@data_app.command("docs")
def data_docs() -> None:
    """List every stored document version with its status and chunk count."""
    settings = get_settings()
    engine = create_db_engine(settings)
    with engine.connect() as connection:
        versions = stored_versions(connection)
    engine.dispose()
    console.print(versions_table(versions, date.today()))


def versions_table(versions: list[StoredVersion], today: date) -> Table:
    table = Table("Document", "Ver", "Status", "Effective", "Review due", "Chunks", "Title")
    for stored in versions:
        status = DocumentStatus(stored.status)
        review = str(stored.review_due or "")
        if status is DocumentStatus.APPROVED and stored.review_overdue(today):
            review = f"[bold red]{review} overdue[/]"
        table.add_row(
            stored.doc_id,
            str(stored.version),
            f"[{STATUS_STYLES[status]}]{status}[/]",
            str(stored.effective_from or ""),
            review,
            str(stored.chunk_count),
            stored.title,
        )
    return table


@data_app.command("load-records")
def data_load_records() -> None:
    """Replace sites, assets, work orders, inspections, incidents and alarms from data/records."""
    settings = get_settings()
    engine = create_db_engine(settings)
    for loaded in load_records(engine, settings.records_dir):
        console.print(f"  {loaded.table:<12} {loaded.rows:>6} rows")
    engine.dispose()
