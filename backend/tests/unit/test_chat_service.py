"""Unit tests for `ChatService`, independent of any real provider or resolver."""

from collections.abc import AsyncIterator

import pytest

from src.models.chat import ChatMessage, ChatRequest, ChatRole
from src.personas.base import PersonaConfig
from src.services.chat_service import ChatService
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.safety.uncensored_guard import UncensoredSafetyGuard


class _RecordingProvider(CompanionModelProvider):
    """Captures the persona it was called with, for assertions."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        self._tokens = tokens or ["hi"]
        self.received_persona: PersonaConfig | None = None

    async def stream_reply(
        self,
        messages: list[ChatMessage],
        persona: PersonaConfig,
        config: ProviderConfig,
    ) -> AsyncIterator[str]:
        self.received_persona = persona
        for token in self._tokens:
            yield token


class _FixedResolver:
    def __init__(self, provider: CompanionModelProvider, is_uncensored: bool) -> None:
        self._provider = provider
        self._is_uncensored = is_uncensored

    def resolve(
        self, requested_model_id: str | None, persona: PersonaConfig
    ) -> tuple[CompanionModelProvider, ProviderConfig, bool]:
        return self._provider, ProviderConfig(model="fake-model"), self._is_uncensored


@pytest.fixture
def request_() -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="hi")])


async def test_uncensored_provider_receives_intimate_mode_persona(request_: ChatRequest) -> None:
    provider = _RecordingProvider()
    service = ChatService(_FixedResolver(provider, is_uncensored=True), UncensoredSafetyGuard())

    async for _ in service.stream_response(request_):
        pass

    assert provider.received_persona is not None
    assert provider.received_persona.mode == "intimate"


async def test_censored_provider_receives_default_mode_persona(request_: ChatRequest) -> None:
    provider = _RecordingProvider()
    service = ChatService(_FixedResolver(provider, is_uncensored=False), UncensoredSafetyGuard())

    async for _ in service.stream_response(request_):
        pass

    assert provider.received_persona is not None
    assert provider.received_persona.mode == "companionship"


async def test_uncensored_provider_blocked_by_safety_guard_never_streams() -> None:
    provider = _RecordingProvider()
    service = ChatService(_FixedResolver(provider, is_uncensored=True), UncensoredSafetyGuard())
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="I want to end my life")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"error"' in chunk for chunk in chunks)
