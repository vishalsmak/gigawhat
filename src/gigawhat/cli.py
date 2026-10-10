import asyncio
import time
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

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
from gigawhat.personas import Persona
from gigawhat.records.load import load_records

if TYPE_CHECKING:
    from gigawhat.assistant.service import Turn
    from gigawhat.evaluation.cases import Case
    from gigawhat.evaluation.checks import CaseResult
    from gigawhat.retrieval.search import RetrievalResult, Retriever

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
    only: Annotated[
        str | None, typer.Option(help="Ingest a single document, e.g. PR-GAS-031.")
    ] = None,
    rebuild: Annotated[
        bool,
        typer.Option(help="Delete stored versions first, e.g. after changing chunking. Dev only."),
    ] = False,
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


@app.command()
def search(
    question: str,
    persona: Annotated[
        Persona, typer.Option(help="Whose access to search with.")
    ] = Persona.GAS_FIELD_ENGINEER,
) -> None:
    """Show the passages retrieval finds for a question, with relevance scores."""
    from gigawhat.retrieval.service import build_retriever

    settings = get_settings()
    retriever = build_retriever(settings)
    result = asyncio.run(_search_and_close(retriever, question, persona))
    enough = "[green]enough evidence[/]" if result.sufficient else "[red]not enough evidence[/]"
    console.print(f"Persona: {persona} · {enough}")
    for passage in result.passages:
        console.print(
            f"\n[bold]{passage.citation}[/] {passage.title}  relevance {passage.relevance:.2f}"
        )
        console.print(passage.text[:400] + ("…" if len(passage.text) > 400 else ""))


async def _search_and_close(
    retriever: "Retriever", question: str, persona: Persona
) -> "RetrievalResult":
    try:
        return await retriever.retrieve(question, persona)
    finally:
        await retriever.aclose()


@app.command()
def ask(
    question: str,
    persona: Annotated[
        Persona, typer.Option(help="Whose role to ask as.")
    ] = Persona.GAS_FIELD_ENGINEER,
) -> None:
    """Ask the assistant a question from the command line, showing each step."""
    from rich.markdown import Markdown

    turn = asyncio.run(_ask_and_close(question, persona))
    console.print(f"\n[bold]Tier:[/] {turn.tier} · [bold]Response:[/] {turn.response.kind}\n")
    console.print(Markdown(turn.response.text))
    for notice in turn.response.notices:
        console.print(f"[yellow]Notice:[/] {notice}")
    for source in turn.response.sources:
        console.print(f"[dim]Source:[/] {source.label} · {source.title}")


async def _ask_and_close(question: str, persona: Persona) -> "Turn":
    from gigawhat.assistant.service import Question, create_assistant

    assistant = await create_assistant(get_settings())
    started = time.monotonic()

    async def show(label: str) -> None:
        console.print(f"  [green]✓[/] {label} [dim]({time.monotonic() - started:.1f}s)[/]")

    try:
        return await assistant.ask(Question(question, persona, "cli"), on_step=show)
    finally:
        await assistant.aclose()


eval_app = typer.Typer(
    help="Evaluation against the golden and red-team sets.", no_args_is_help=True
)
app.add_typer(eval_app, name="eval")
EVAL_SUITES = {"golden": Path("evals/golden.yaml"), "redteam": Path("evals/redteam.yaml")}
EVAL_REPORTS = Path("evals/reports")


# Each parameter is one of the command's options, so this is the one place more than three is fine.
@eval_app.command("run")
def eval_run(
    suite: Annotated[list[str], typer.Option(help="golden, redteam, or both.")] = ["golden"],  # noqa: B006
    limit: Annotated[int | None, typer.Option(help="Only the first N cases of each suite.")] = None,
    concurrency: Annotated[int, typer.Option(help="Cases run at once.")] = 1,
    judge: Annotated[bool, typer.Option(help="Also score answers with DeepEval.")] = False,
) -> None:
    """Run the evaluation, write a report to evals/reports, and fail if a release gate fails."""
    from gigawhat.evaluation.cases import load_cases
    from gigawhat.evaluation.report import all_gates_pass, markdown

    settings = get_settings()
    cases = [case for name in suite for case in load_cases(EVAL_SUITES[name])[:limit]]
    results = asyncio.run(_evaluate(cases, concurrency, judge))
    stamp = date.today().isoformat()
    title = f"GigaWhat evaluation · {'+'.join(suite)} · {settings.profile} profile · {stamp}"
    EVAL_REPORTS.mkdir(parents=True, exist_ok=True)
    report = EVAL_REPORTS / f"{stamp}-{settings.profile}-{'-'.join(suite)}.md"
    report.write_text(markdown(results, title))
    console.print(f"Report: {report}")
    if not all_gates_pass(results):
        console.print("[bold red]A release gate failed.[/]")
        raise typer.Exit(code=1)
    console.print("[bold green]All release gates passed.[/]")


async def _evaluate(cases: list["Case"], concurrency: int, judge: bool) -> list["CaseResult"]:
    from gigawhat.assistant.service import create_assistant
    from gigawhat.evaluation.judge import build_judge
    from gigawhat.evaluation.runner import Evaluator, run_cases
    from gigawhat.models import chat_model_name, create_answer_model

    settings = get_settings()
    assistant = await create_assistant(settings)
    judge_model = (
        build_judge(create_answer_model(settings), chat_model_name(settings)) if judge else None
    )
    try:
        return await run_cases(Evaluator(assistant, judge_model), cases, concurrency)
    finally:
        await assistant.aclose()
