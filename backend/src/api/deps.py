"""FastAPI dependency wiring.

Centralizing construction here (rather than instantiating providers/services
inline in route handlers) is also what makes `test_chat_endpoint.py` able to
swap in a fake provider via `app.dependency_overrides[get_provider]` without
touching the route or service code.
"""

from functools import lru_cache

import anthropic
from fastapi import Depends

from src.config import Settings, get_settings
from src.services.chat_service import ChatService
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.claude_provider import ClaudeProvider


@lru_cache
def get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Return a process-wide `AsyncAnthropic` client, built from settings."""
    settings = get_settings()
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def get_provider(
    client: anthropic.AsyncAnthropic = Depends(get_anthropic_client),
) -> CompanionModelProvider:
    """Return the active `CompanionModelProvider` implementation."""
    return ClaudeProvider(client)


def get_chat_service(
    provider: CompanionModelProvider = Depends(get_provider),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """Return a `ChatService` wired to the active provider and model settings."""
    return ChatService(provider, ProviderConfig(model=settings.claude_model))
