"""Input guardrails with NVIDIA NeMo Guardrails: jailbreaks, prompt injection and off-topic use."""

from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import RailStatus

from gigawhat.assistant.prompts import rails_config_yaml


@dataclass(frozen=True)
class RailsVerdict:
    allowed: bool
    rail: str | None = None


class ConfiguredSettingsModel(BaseChatModel):
    """Passes NeMo's calls to our model with the settings we configured.

    NeMo binds temperature and max_tokens to every call. Ollama's client rejects them as
    keyword arguments and Claude Opus 5.5 rejects temperature outright, so they are dropped
    and the model keeps its own settings.
    """

    inner: BaseChatModel

    @property
    def _llm_type(self) -> str:
        return f"configured-{self.inner._llm_type}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **ignored: Any,
    ) -> ChatResult:
        return self.inner._generate(messages, stop=stop)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **ignored: Any,
    ) -> ChatResult:
        return await self.inner._agenerate(messages, stop=stop)


class InputRails:
    def __init__(self, model: BaseChatModel) -> None:
        config = RailsConfig.from_content(yaml_content=rails_config_yaml())
        self._rails = LLMRails(config, llm=ConfiguredSettingsModel(inner=model))

    async def check(self, question: str) -> RailsVerdict:
        result = await self._rails.check_async([{"role": "user", "content": question}])
        if result.status is RailStatus.BLOCKED:
            return RailsVerdict(allowed=False, rail=result.rail)
        return RailsVerdict(allowed=True)
