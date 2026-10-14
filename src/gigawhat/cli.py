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
from gigawhat.doctor import Status, run_checks
from gigawhat.identity.personas import Persona
from gigawhat.ingestion.catalogue import StoredVersion, stored_versions
from gigawhat.ingestion.hse import fetch_guidance
from gigawhat.ingestion.register import DocumentStatus, load_register
from gigawhat.observability.logs import configure_logging
from gigawhat.records.load import load_records
from gigawhat.storage.db import create_db_engine, upgrade_to_head

if TYPE_CHECKING:
    from gigawhat.evaluation.runner import Evaluation, EvaluationPlan
    from gigawhat.orchestration.service import Turn
    from gigawhat.retrieval.search import RetrievalResult, Retriever

HTTP_TIMEOUT_SECONDS = 3.0
DOWNLOAD_TIMEOUT_SECONDS = 120.0
PASSAGE_PREVIEW_CHARS = 400
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
# The CLI prints its own readable output; structured logs show only what went wrong.
CLI_LOG_LEVEL = "WARNING"


@app.callback()
def main() -> None:
    configure_logging(CLI_LOG_LEVEL)


@app.command()
def doctor() -> None:
    """Check the database, each model role and its limits, and tracing."""
    settings = get_settings()
    console.print(f"Profile: {settings.profile}")
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as http:
        checks = run_checks(settings, http)
    for check in checks:
        console.print(f"  {STATUS_MARKS[check.status]} {check.name:<10} {check.detail}")
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
    from gigawhat.ingestion.pipeline import build_ingestor

    settings = get_settings()
    register = load_register(settings.register_path)
    selected = [d for d in register.documents if only is None or d.doc_id == only]
    if not selected:
        raise typer.BadParameter(f"{only} is not in the register", param_hint="--only")

    if rebuild:
        typer.confirm(
            f"Delete every stored version of {only or 'all documents'} in {settings.database}?",
            abort=True,
        )
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
    from gigawhat.providers.registry import ModelRegistry
    from gigawhat.retrieval.search import Retriever

    settings = get_settings()
    models = ModelRegistry(settings)
    retriever = Retriever(settings, models.embeddings(), models.reranker())
    result = asyncio.run(_search_and_close(retriever, question, persona))
    enough = "[green]enough evidence[/]" if result.sufficient else "[red]not enough evidence[/]"
    console.print(f"Persona: {persona} · {enough}")
    for passage in result.passages:
        console.print(
            f"\n[bold]{passage.citation}[/] {passage.title}  relevance {passage.relevance:.2f}"
        )
        preview = passage.text[:PASSAGE_PREVIEW_CHARS]
        console.print(preview + ("…" if len(passage.text) > PASSAGE_PREVIEW_CHARS else ""))


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
    from gigawhat.observability.tracing import create_tracer
    from gigawhat.orchestration.service import Question, create_assistant

    settings = get_settings()
    assistant = await create_assistant(settings, create_tracer(settings))
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
    """Run the evaluation, write a report to evals/reports, and fail if a release gate fails.

    With a LangSmith key on the cloud profile, the run is also a LangSmith experiment.
    """
    from gigawhat.evaluation.cases import load_cases
    from gigawhat.evaluation.report import all_gates_pass, markdown
    from gigawhat.evaluation.runner import EvaluationPlan

    settings = get_settings()
    plan = EvaluationPlan(
        {name: load_cases(EVAL_SUITES[name]) for name in suite}, limit, concurrency, judge
    )
    evaluation = asyncio.run(_evaluate(plan))
    stamp = date.today().isoformat()
    title = f"GigaWhat evaluation · {'+'.join(suite)} · {settings.profile} profile · {stamp}"
    EVAL_REPORTS.mkdir(parents=True, exist_ok=True)
    report = EVAL_REPORTS / report_name(stamp, str(settings.profile), plan)
    experiment = evaluation.experiment
    report.write_text(markdown(evaluation.results, title, experiment.name if experiment else None))
    console.print(f"Report: {report}")
    if experiment:
        console.print(f"LangSmith experiment: {experiment.url}")
    if not all_gates_pass(evaluation.results):
        console.print("[bold red]A release gate failed.[/]")
        raise typer.Exit(code=1)
    console.print("[bold green]All release gates passed.[/]")


def report_name(stamp: str, profile: str, plan: "EvaluationPlan") -> str:
    """A limited run is named apart, so it never overwrites the report of a full run."""
    limited = f"-limit{plan.limit}" if plan.limit else ""
    return f"{stamp}-{profile}-{'-'.join(plan.suites)}{limited}.md"


async def _evaluate(plan: "EvaluationPlan") -> "Evaluation":
    """A LangSmith experiment when LangSmith may be used, otherwise a run on this machine. The
    assistant gets no tracer of its own: the experiment traces each case."""
    from gigawhat.evaluation.experiment import run_experiment
    from gigawhat.evaluation.judge import build_judge
    from gigawhat.evaluation.runner import Evaluation, Evaluator, run_cases
    from gigawhat.observability.tracing import langsmith_client
    from gigawhat.orchestration.service import create_assistant
    from gigawhat.providers.registry import ChatRole, ModelRegistry

    settings = get_settings()
    models = ModelRegistry(settings)
    judge_model = (
        build_judge(models.chat(ChatRole.ANSWER), str(models.chat_choice(ChatRole.ANSWER)))
        if plan.judge
        else None
    )
    evaluator = Evaluator(await create_assistant(settings, tracer=None), judge_model)
    client = langsmith_client(settings)
    try:
        if client is None:
            return Evaluation(await run_cases(evaluator, plan.cases, plan.concurrency))
        return await run_experiment(evaluator, plan, client)
    finally:
        await evaluator.assistant.aclose()
