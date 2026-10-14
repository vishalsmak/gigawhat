"""Optional LangSmith tracing and evaluation. Off unless a key is set, and never offline."""

from langchain_core.tracers import LangChainTracer
from langsmith import Client

from gigawhat.config import Profile, Settings

# Long enough for a final batch to reach LangSmith; short enough that an outage can't stall exit.
FLUSH_TIMEOUT_SECONDS = 10


def langsmith_client(settings: Settings) -> Client | None:
    """The one place that decides whether anything may go to LangSmith. Never on the offline
    profile, whose promise is that nothing leaves the machine."""
    if settings.profile is Profile.OFFLINE or settings.langsmith_api_key is None:
        return None
    return Client(
        api_url=settings.langsmith_endpoint,
        api_key=settings.langsmith_api_key.get_secret_value(),
    )


def create_tracer(settings: Settings) -> LangChainTracer | None:
    """The tracer is passed to each run rather than switched on with LANGSMITH_TRACING, which would
    trace every LangChain call in the process, whatever the profile."""
    client = langsmith_client(settings)
    if client is None:
        return None
    return LangChainTracer(project_name=settings.langsmith_project, client=client)


def flush(tracer: LangChainTracer) -> None:
    """Sends traces still queued in the background, so a short CLI run doesn't drop them."""
    tracer.wait_for_futures()
    tracer.client.flush(timeout=FLUSH_TIMEOUT_SECONDS)
