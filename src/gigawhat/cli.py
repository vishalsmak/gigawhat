import httpx
import typer

from gigawhat.config import get_settings
from gigawhat.db import upgrade_to_head
from gigawhat.doctor import Status, run_checks

HTTP_TIMEOUT_SECONDS = 3.0
STATUS_MARKS = {Status.OK: "✔", Status.WARN: "!", Status.FAIL: "✘"}

app = typer.Typer(help="GigaWhat operational assistant.", no_args_is_help=True)
db_app = typer.Typer(help="Database schema.", no_args_is_help=True)
app.add_typer(db_app, name="db")


@app.command()
def doctor() -> None:
    """Check that the database, models and tracing are ready for the current profile."""
    settings = get_settings()
    typer.echo(f"Profile: {settings.profile}")
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as http:
        checks = run_checks(settings, http)
    for check in checks:
        typer.echo(f"  {STATUS_MARKS[check.status]} {check.name:<9} {check.detail}")
    if any(check.status is Status.FAIL for check in checks):
        raise typer.Exit(code=1)


@db_app.command("upgrade")
def db_upgrade() -> None:
    """Apply all pending migrations to the current profile's database."""
    settings = get_settings()
    upgrade_to_head(settings)
    typer.echo(f"{settings.database} is up to date.")
