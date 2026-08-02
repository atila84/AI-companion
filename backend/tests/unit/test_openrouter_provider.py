"""Unit tests for `OpenAICompatibleProvider` (exercised via `OpenRouterProvider`).

The `openai` SDK client is always faked — no real network call, no real API
key needed. `OpenAIProvider`/`OllamaProvider` share the same base class and
are covered by these same code paths.
"""

from collections.abc import AsyncIterator
from types import SimpleNamespace

import openai
import pytest

from src.models.chat import ChatMessage, ChatRole
from src.personas.base import PersonaConfig
from src.services.providers.base import ProviderConfig
from src.services.providers.exceptions import ProviderAPIError
from src.services.providers.openrouter_provider import OpenRouterProvider


def _chunk(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


class _FakeChatCompletionStream:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    def __aiter__(self) -> AsyncIterator[SimpleNamespace]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[SimpleNamespace]:
        for token in self._tokens:
            yield _chunk(token)


class _FakeCompletions:
    def __init__(self, tokens: list[str] | None = None, error: Exception | None = None) -> None:
        self._tokens = tokens or []
        self._error = error

    async def create(self, **kwargs: object) -> _FakeChatCompletionStream:
        if self._error is not None:
            raise self._error
        return _FakeChatCompletionStream(self._tokens)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeAsyncOpenAI:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


@pytest.fixture
def messages() -> list[ChatMessage]:
    return [ChatMessage(role=ChatRole.USER, content="hello")]


@pytest.fixture
def persona() -> PersonaConfig:
    return PersonaConfig()


@pytest.fixture
def provider_config() -> ProviderConfig:
    return ProviderConfig(model="cognitivecomputations/dolphin-mixtral-8x22b")


async def test_stream_reply_yields_tokens_in_order(
    messages: list[ChatMessage], persona: PersonaConfig, provider_config: ProviderConfig
) -> None:
    fake_client = _FakeAsyncOpenAI(_FakeCompletions(tokens=["Hello", " ", "world"]))
    provider = OpenRouterProvider(fake_client)  # type: ignore[arg-type]

    received = [token async for token in provider.stream_reply(messages, persona, provider_config)]

    assert received == ["Hello", " ", "world"]


async def test_stream_reply_skips_empty_deltas(
    messages: list[ChatMessage], persona: PersonaConfig, provider_config: ProviderConfig
) -> None:
    fake_client = _FakeAsyncOpenAI(_FakeCompletions(tokens=["Hello", None, "world"]))  # type: ignore[list-item]
    provider = OpenRouterProvider(fake_client)  # type: ignore[arg-type]

    received = [token async for token in provider.stream_reply(messages, persona, provider_config)]

    assert received == ["Hello", "world"]


async def test_stream_reply_wraps_api_error(
    messages: list[ChatMessage], persona: PersonaConfig, provider_config: ProviderConfig
) -> None:
    api_error = openai.APIError("boom", request=SimpleNamespace(), body=None)
    fake_client = _FakeAsyncOpenAI(_FakeCompletions(error=api_error))
    provider = OpenRouterProvider(fake_client)  # type: ignore[arg-type]

    with pytest.raises(ProviderAPIError):
        async for _ in provider.stream_reply(messages, persona, provider_config):
            pass
