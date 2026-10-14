"""Input guardrails with NVIDIA NeMo Guardrails: jailbreaks, prompt injection and off-topic use."""

import os
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LangSmithParams
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.integrations.langchain.llm_adapter import LangChainLLMAdapter
from nemoguardrails.rails.llm.options import RailStatus

from gigawhat.prompts import rails_config_yaml

# NeMo Guardrails reports anonymous usage statistics to NVIDIA unless told not to. It checks when
# rails run, so setting it here is early enough.
os.environ.setdefault("NEMO_GUARDRAILS_NO_USAGE_STATS", "1")


@dataclass(frozen=True)
class RailsVerdict:
    allowed: bool
    rail: str | None = None


class ConfiguredSettingsModel(BaseChatModel):
    """Passes NeMo's calls to our model with the settings we configured.

    NeMo binds temperature and max_tokens to every call. Ollama's client rejects them as
    keyword arguments, and elsewhere they would override the role's settings in the model
    registry, so they are dropped and the model keeps its own settings. Calling the inner model's
    _agenerate skips its rate limiter, so the wrapper takes the same one.
    """

    inner: BaseChatModel

    @property
    def _llm_type(self) -> str:
        return f"configured-{self.inner._llm_type}"

    def _get_ls_params(self, stop: list[str] | None = None, **kwargs: Any) -> LangSmithParams:
        """Traces name the model that answers, not this wrapper."""
        return self.inner._get_ls_params(stop=stop, **kwargs)

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
        configured = ConfiguredSettingsModel(inner=model, rate_limiter=model.rate_limiter)
        self._rails = LLMRails(config, llm=LangChainLLMAdapter(configured))

    async def check(self, question: str) -> RailsVerdict:
        result = await self._rails.check_async([{"role": "user", "content": question}])
        if result.status is RailStatus.BLOCKED:
            return RailsVerdict(allowed=False, rail=result.rail)
        return RailsVerdict(allowed=True)
