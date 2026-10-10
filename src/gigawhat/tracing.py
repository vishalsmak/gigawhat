"""Optional Langfuse tracing of every model, tool and graph step. Off unless keys are set."""

from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from gigawhat.config import Profile, Settings


def create_tracer(settings: Settings) -> BaseCallbackHandler | None:
    """Never on the offline profile, whose promise is that nothing leaves the machine."""
    if settings.profile is Profile.OFFLINE:
        return None
    if not settings.tracing_enabled or settings.langfuse_secret_key is None:
        return None
    # The client registers itself; the handler finds it by public key.
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=settings.langfuse_host,
    )
    return CallbackHandler(public_key=settings.langfuse_public_key)
