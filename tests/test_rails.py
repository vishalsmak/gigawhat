from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.rate_limiters import BaseRateLimiter
from langchain_ollama import ChatOllama

from gigawhat.assistant.rails import ConfiguredSettingsModel, InputRails


class CountingLimiter(BaseRateLimiter):
    def __init__(self) -> None:
        self.acquired = 0

    def acquire(self, *, blocking: bool = True) -> bool:
        self.acquired += 1
        return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        return self.acquire(blocking=blocking)


class AllowEverything(BaseChatModel):
    """Answers NeMo's 'should this be blocked?' with No."""

    @property
    def _llm_type(self) -> str:
        return "allow-everything"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage("No"))])


async def test_input_check_waits_for_the_models_rate_limiter() -> None:
    limiter = CountingLimiter()
    rails = InputRails(AllowEverything(rate_limiter=limiter))

    await rails.check("Who owns PR-ELEC-044?")

    assert limiter.acquired == 1


def test_traces_name_the_model_behind_the_input_check() -> None:
    wrapped = ConfiguredSettingsModel(inner=ChatOllama(model="gpt-oss:20b"))

    assert wrapped._get_ls_params()["ls_model_name"] == "gpt-oss:20b"
