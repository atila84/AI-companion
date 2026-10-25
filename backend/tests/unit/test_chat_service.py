"""Unit tests for `ChatService`, independent of any real provider or resolver."""

from collections.abc import AsyncIterator

import pytest

from src.models.chat import ChatMessage, ChatRequest, ChatRole
from src.personas.base import PersonaConfig
from src.services.chat_service import ChatService
from src.services.image_providers.base import ImageGenerationConfig, ImageGenerationProvider
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.exceptions import ProviderConfigError
from src.services.safety.image_content_guard import ImageContentGuard
from src.services.safety.uncensored_guard import UncensoredSafetyGuard
from src.services.safety.video_content_guard import VideoContentGuard
from src.services.video_providers.base import VideoGenerationConfig, VideoGenerationProvider


class _StubImageProvider(ImageGenerationProvider):
    async def generate_image(self, prompt: str, config: ImageGenerationConfig) -> str:
        return "https://example.com/image.png"


class _StubImageResolver:
    """Records the model id it was asked for, for forwarding assertions."""

    def __init__(self) -> None:
        self.received_model_id: str | None = None
        self.was_called = False

    def resolve(
        self, requested_model_id: str | None = None
    ) -> tuple[ImageGenerationProvider, ImageGenerationConfig]:
        self.received_model_id = requested_model_id
        self.was_called = True
        return _StubImageProvider(), ImageGenerationConfig(model="fake-image-model")


class _StubVideoProvider(VideoGenerationProvider):
    async def generate_video(self, prompt: str, config: VideoGenerationConfig) -> str:
        return "https://example.com/video.mp4"


class _StubVideoResolver:
    """Records the model id it was asked for, for forwarding assertions."""

    def __init__(self) -> None:
        self.received_model_id: str | None = None
        self.was_called = False

    def resolve(
        self, requested_model_id: str | None = None
    ) -> tuple[VideoGenerationProvider, VideoGenerationConfig]:
        self.received_model_id = requested_model_id
        self.was_called = True
        return _StubVideoProvider(), VideoGenerationConfig(model="fake-video-model")


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
    service = ChatService(
        _FixedResolver(provider, is_uncensored=True), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )

    async for _ in service.stream_response(request_):
        pass

    assert provider.received_persona is not None
    assert provider.received_persona.mode == "intimate"


async def test_censored_provider_receives_default_mode_persona(request_: ChatRequest) -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=False), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )

    async for _ in service.stream_response(request_):
        pass

    assert provider.received_persona is not None
    assert provider.received_persona.mode == "companionship"


async def test_uncensored_provider_blocked_by_safety_guard_never_streams() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=True), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="I want to end my life")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"error"' in chunk for chunk in chunks)


async def test_image_intent_short_circuits_the_text_provider() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=False), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="draw me a sunset")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"image"' in chunk and "example.com/image.png" in chunk for chunk in chunks)
    assert any('"type":"done"' in chunk for chunk in chunks)


async def test_crisis_phrase_is_caught_even_when_message_also_matches_image_intent() -> None:
    """Finding 1 regression: a bare "draw" trigger must not bypass the crisis guard."""
    provider = _RecordingProvider()

    class _FailingImageResolver:
        def resolve(
            self, requested_model_id: str | None = None
        ) -> tuple[ImageGenerationProvider, ImageGenerationConfig]:
            raise AssertionError("Should not be called once the crisis guard intervenes")

    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _FailingImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(
        messages=[
            ChatMessage(
                role=ChatRole.USER,
                content="I've been meaning to draw more but I want to end my life honestly.",
            )
        ]
    )

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"error"' in chunk for chunk in chunks)
    assert not any('"type":"image"' in chunk for chunk in chunks)


async def test_image_intent_blocked_by_sexual_content_when_not_uncensored() -> None:
    """Finding 2 regression: companionship mode must not get explicit images.

    "show me a nude picture of you" extracts to just "you" (the descriptor
    is stranded before the "of X" clause), so the guard must be checking the
    raw message, not the extracted generation prompt, to catch this.
    """
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=False), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="show me a nude picture of you")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"error"' in chunk for chunk in chunks)
    assert not any('"type":"image"' in chunk for chunk in chunks)


async def test_image_intent_allows_sexual_content_when_uncensored() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=True), UncensoredSafetyGuard(), _StubImageResolver(), ImageContentGuard(), _StubVideoResolver(), VideoContentGuard()
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="show me a nude picture of you")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"image"' in chunk for chunk in chunks)


async def test_image_intent_blocked_by_content_guard_never_calls_provider() -> None:
    provider = _RecordingProvider()

    class _FailingImageResolver:
        def resolve(self, requested_model_id: str | None = None) -> tuple[ImageGenerationProvider, ImageGenerationConfig]:
            raise AssertionError("Should not be called once the content guard blocks the prompt")

    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _FailingImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="draw a non-consensual scene")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"error"' in chunk for chunk in chunks)


async def test_video_intent_short_circuits_the_text_provider() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="generate a video of a sunset")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"video"' in chunk and "example.com/video.mp4" in chunk for chunk in chunks)
    assert any('"type":"done"' in chunk for chunk in chunks)


async def test_crisis_phrase_is_caught_even_when_message_also_matches_video_intent() -> None:
    provider = _RecordingProvider()

    class _FailingVideoResolver:
        def resolve(
            self, requested_model_id: str | None = None
        ) -> tuple[VideoGenerationProvider, VideoGenerationConfig]:
            raise AssertionError("Should not be called once the crisis guard intervenes")

    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        _FailingVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(
        messages=[
            ChatMessage(
                role=ChatRole.USER,
                content="animate me something but honestly I want to end my life.",
            )
        ]
    )

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert provider.received_persona is None
    assert any('"type":"error"' in chunk for chunk in chunks)
    assert not any('"type":"video"' in chunk for chunk in chunks)


async def test_video_intent_blocked_by_sexual_content_when_not_uncensored() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="make me a nude video of you")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"error"' in chunk for chunk in chunks)
    assert not any('"type":"video"' in chunk for chunk in chunks)


async def test_video_intent_allows_sexual_content_when_uncensored() -> None:
    provider = _RecordingProvider()
    service = ChatService(
        _FixedResolver(provider, is_uncensored=True),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="make me a nude video of you")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"video"' in chunk for chunk in chunks)


async def test_video_intent_blocked_by_content_guard_never_calls_provider() -> None:
    provider = _RecordingProvider()

    class _FailingVideoResolver:
        def resolve(
            self, requested_model_id: str | None = None
        ) -> tuple[VideoGenerationProvider, VideoGenerationConfig]:
            raise AssertionError("Should not be called once the content guard blocks the prompt")

    service = ChatService(
        _FixedResolver(provider, is_uncensored=False),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        _FailingVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="animate a non-consensual scene")])

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"error"' in chunk for chunk in chunks)


async def test_image_model_id_is_forwarded_to_the_image_resolver() -> None:
    """The UI's image-model selection must reach the resolver, not be dropped."""
    image_resolver = _StubImageResolver()
    service = ChatService(
        _FixedResolver(_RecordingProvider(), is_uncensored=False),
        UncensoredSafetyGuard(),
        image_resolver,
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(
        messages=[ChatMessage(role=ChatRole.USER, content="draw me a sunset")],
        image_model_id="pollinations/turbo",
    )

    async for _ in service.stream_response(request):
        pass

    assert image_resolver.received_model_id == "pollinations/turbo"


async def test_omitted_image_model_id_defers_to_the_backend_default() -> None:
    image_resolver = _StubImageResolver()
    service = ChatService(
        _FixedResolver(_RecordingProvider(), is_uncensored=False),
        UncensoredSafetyGuard(),
        image_resolver,
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(messages=[ChatMessage(role=ChatRole.USER, content="draw me a sunset")])

    async for _ in service.stream_response(request):
        pass

    assert image_resolver.was_called
    assert image_resolver.received_model_id is None


async def test_video_model_id_is_forwarded_to_the_video_resolver() -> None:
    video_resolver = _StubVideoResolver()
    service = ChatService(
        _FixedResolver(_RecordingProvider(), is_uncensored=False),
        UncensoredSafetyGuard(),
        _StubImageResolver(),
        ImageContentGuard(),
        video_resolver,
        VideoContentGuard(),
    )
    request = ChatRequest(
        messages=[ChatMessage(role=ChatRole.USER, content="generate a video of a sunset")],
        video_model_id="comfyui/wan2.2",
    )

    async for _ in service.stream_response(request):
        pass

    assert video_resolver.received_model_id == "comfyui/wan2.2"


async def test_unknown_image_model_id_yields_an_error_chunk_not_a_crash() -> None:
    """A stale/disabled selection must degrade to a clean ERROR chunk."""

    class _RaisingImageResolver:
        def resolve(
            self, requested_model_id: str | None = None
        ) -> tuple[ImageGenerationProvider, ImageGenerationConfig]:
            raise ProviderConfigError(f"Unknown or disabled image model_id: {requested_model_id!r}")

    service = ChatService(
        _FixedResolver(_RecordingProvider(), is_uncensored=False),
        UncensoredSafetyGuard(),
        _RaisingImageResolver(),
        ImageContentGuard(),
        _StubVideoResolver(),
        VideoContentGuard(),
    )
    request = ChatRequest(
        messages=[ChatMessage(role=ChatRole.USER, content="draw me a sunset")],
        image_model_id="deleted/model",
    )

    chunks = [chunk async for chunk in service.stream_response(request)]

    assert any('"type":"error"' in chunk and "deleted/model" in chunk for chunk in chunks)
    assert not any('"type":"image"' in chunk for chunk in chunks)
