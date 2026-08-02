"""Unit tests for `ClaudeProvider`. The Anthropic client is always faked — no
real network call, no real API key needed."""

from collections.abc import AsyncIterator

import anthropic
import pytest

from src.models.chat import ChatMessage, ChatRole
from src.personas.base import PersonaConfig
from src.services.providers.base import ProviderConfig
from src.services.providers.claude_provider import ClaudeProvider
from src.services.providers.exceptions import ProviderAPIError


class _FakeTextStream:
    """Stands in for the Anthropic SDK's `stream.text_stream` async iterator."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        for token in self._tokens:
            yield token


class _FakeStreamContextManager:
    """Stands in for the object returned by `client.messages.stream(...)`."""

    def __init__(self, tokens: list[str] | None = None, error: Exception | None = None) -> None:
        self._tokens = tokens or []
        self._error = error
        self.text_stream = _FakeTextStream(self._tokens)

    async def __aenter__(self) -> "_FakeStreamContextManager":
        if self._error is not None:
            raise self._error
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeMessages:
    def __init__(self, stream_cm: _FakeStreamContextManager) -> None:
        self._stream_cm = stream_cm

    def stream(self, **kwargs: object) -> _FakeStreamContextManager:
        return self._stream_cm


class _FakeAsyncAnthropic:
    def __init__(self, stream_cm: _FakeStreamContextManager) -> None:
        self.messages = _FakeMessages(stream_cm)


@pytest.fixture
def messages() -> list[ChatMessage]:
    return [ChatMessage(role=ChatRole.USER, content="hello")]


@pytest.fixture
def persona() -> PersonaConfig:
    return PersonaConfig()


@pytest.fixture
def provider_config() -> ProviderConfig:
    return ProviderConfig(model="claude-opus-5")


async def test_stream_reply_yields_tokens_in_order(
    messages: list[ChatMessage], persona: PersonaConfig, provider_config: ProviderConfig
) -> None:
    fake_client = _FakeAsyncAnthropic(_FakeStreamContextManager(tokens=["Hello", " ", "world"]))
    provider = ClaudeProvider(fake_client)  # type: ignore[arg-type]

    received = [token async for token in provider.stream_reply(messages, persona, provider_config)]

    assert received == ["Hello", " ", "world"]


async def test_stream_reply_wraps_api_error(
    messages: list[ChatMessage], persona: PersonaConfig, provider_config: ProviderConfig
) -> None:
    api_error = anthropic.APIError("boom", request=None, body=None)  # type: ignore[call-arg]
    fake_client = _FakeAsyncAnthropic(_FakeStreamContextManager(error=api_error))
    provider = ClaudeProvider(fake_client)  # type: ignore[arg-type]

    with pytest.raises(ProviderAPIError):
        async for _ in provider.stream_reply(messages, persona, provider_config):
            pass
