from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.config import get_config, LLMConfig


@dataclass
class AgentContext:
    """Context passed to every agent on invocation."""
    tools: List[Callable] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base for all HVAC agents."""

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        context: Optional[AgentContext] = None,
    ):
        self.name = name
        self.llm = llm
        self.context = context or AgentContext()

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic."""
        ...

    def reset_context(self, ctx: AgentContext) -> None:
        """Replace the current context with a new one."""
        self.context = ctx


def create_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    deep: bool = True,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    **kwargs,
) -> BaseChatModel:
    """Factory for creating LLM clients with Deep/Quick model selection.

    Args:
        provider: "anthropic" (default), "openai", or "google". Uses config if None.
        model: Override model name. If None, picks deep_model or quick_model from config.
        deep: If True and model not specified, use deep model (Sonnet). Else quick (Haiku).
        api_key: Override API key. Uses config if None.
        base_url: Override base URL. Uses config if None.
        temperature: LLM temperature.
        max_tokens: Max output tokens.
        **kwargs: Additional arguments passed to the ChatModel constructor.

    Returns:
        LangChain BaseChatModel instance.

    Raises:
        NotImplementedError: If provider is "google" (not yet supported).
        ValueError: If provider is unknown.
    """
    # Resolve provider/config fallbacks
    if provider is None:
        provider = get_config().llm.provider

    # Resolve model if not explicitly provided
    if model is None:
        llm_config = get_config().llm
        model = llm_config.deep_model if deep else llm_config.quick_model

    # Resolve api_key and base_url from config if not explicitly provided
    if api_key is None:
        api_key = get_config().llm.api_key
    if base_url is None:
        base_url = get_config().llm.base_url

    # Common kwargs to pass to all ChatModel constructors
    common_kwargs: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key is not None:
        common_kwargs["api_key"] = api_key
    if base_url is not None:
        common_kwargs["base_url"] = base_url
    # Merge in any extra kwargs
    common_kwargs.update(kwargs)

    if provider == "anthropic":
        return ChatAnthropic(**common_kwargs)
    elif provider == "openai":
        return ChatOpenAI(**common_kwargs)
    elif provider == "google":
        raise NotImplementedError("Google provider not yet supported")
    else:
        raise ValueError(
            f"Unsupported provider: '{provider}'. "
            "Supported providers: anthropic, openai"
        )
