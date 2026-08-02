"""Factory for turning a `ProviderId` into a `CompanionModelProvider`.

Adding a new backend means writing one `CompanionModelProvider` subclass
(the Strategy) and registering it in `_PROVIDER_FACTORIES` here (the
Factory) — no other call site needs to change. This is a deliberately dumb
dict lookup, not a plugin-discovery mechanism: no hot reload, no dynamic
import scanning.
"""

from collections.abc import Callable
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

import anthropic
import openai

from src.services.providers.base import CompanionModelProvider
from src.services.providers.claude_provider import ClaudeProvider
from src.services.providers.exceptions import ProviderConfigError
from src.services.providers.ollama_provider import OllamaProvider
from src.services.providers.openai_provider import OpenAIProvider
from src.services.providers.openrouter_provider import OPENROUTER_BASE_URL, OpenRouterProvider

if TYPE_CHECKING:
    from src.config import Settings


class ProviderId(str, Enum):
    """Identifies which `CompanionModelProvider` implementation to use."""

    CLAUDE = "claude"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    OLLAMA = "ollama"


@lru_cache
def _anthropic_client(api_key: str) -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=api_key)


@lru_cache
def _openai_client(api_key: str, base_url: str | None) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=api_key, base_url=base_url)


def _build_claude(settings: "Settings") -> CompanionModelProvider:
    return ClaudeProvider(_anthropic_client(settings.anthropic_api_key))


def _build_openrouter(settings: "Settings") -> CompanionModelProvider:
    if not settings.openrouter_api_key:
        raise ProviderConfigError("OPENROUTER_API_KEY is not set.")
    client = _openai_client(settings.openrouter_api_key, OPENROUTER_BASE_URL)
    return OpenRouterProvider(client)


def _build_openai(settings: "Settings") -> CompanionModelProvider:
    if not settings.openai_api_key:
        raise ProviderConfigError("OPENAI_API_KEY is not set.")
    client = _openai_client(settings.openai_api_key, None)
    return OpenAIProvider(client)


def _build_ollama(settings: "Settings") -> CompanionModelProvider:
    if not settings.ollama_base_url:
        raise ProviderConfigError("OLLAMA_BASE_URL is not set.")
    # Ollama's OpenAI-compatible endpoint does not check the API key, but the
    # SDK requires a non-empty value to be supplied.
    client = _openai_client("ollama", settings.ollama_base_url)
    return OllamaProvider(client)


_PROVIDER_FACTORIES: dict[ProviderId, "Callable[[Settings], CompanionModelProvider]"] = {
    ProviderId.CLAUDE: _build_claude,
    ProviderId.OPENROUTER: _build_openrouter,
    ProviderId.OPENAI: _build_openai,
    ProviderId.OLLAMA: _build_ollama,
}


def build_provider(provider_id: ProviderId, settings: "Settings") -> CompanionModelProvider:
    """Build (or return a cached) `CompanionModelProvider` for `provider_id`.

    Args:
        provider_id: Which provider implementation to build.
        settings: Application settings, supplying credentials/endpoints.

    Returns:
        A ready-to-use `CompanionModelProvider`.

    Raises:
        ProviderConfigError: `provider_id` is unknown, or its required
            credentials are not configured.
    """
    factory = _PROVIDER_FACTORIES.get(provider_id)
    if factory is None:
        raise ProviderConfigError(f"Unknown provider: {provider_id!r}")
    return factory(settings)
