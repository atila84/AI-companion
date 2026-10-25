"""Orchestrates persona wrapping, provider resolution, and streaming for one chat turn."""

from collections.abc import AsyncIterator

from src.models.chat import ChatRequest, StreamChunk, StreamChunkType
from src.personas.base import PersonaConfig
from src.services.image_intent import detect_image_prompt
from src.services.image_router import ImageProviderResolver
from src.services.provider_router import ProviderResolver
from src.services.providers.exceptions import ProviderError
from src.services.safety.exceptions import SafetyInterventionError
from src.services.safety.image_content_guard import ImageContentGuard
from src.services.safety.uncensored_guard import UncensoredSafetyGuard
from src.services.safety.video_content_guard import VideoContentGuard
from src.services.video_intent import detect_video_prompt
from src.services.video_router import VideoProviderResolver
from src.utils.sse import format_sse


class ChatService:
    """Turns a `ChatRequest` into a stream of SSE-framed `StreamChunk`s."""

    def __init__(
        self,
        resolver: ProviderResolver,
        safety_guard: UncensoredSafetyGuard,
        image_resolver: ImageProviderResolver,
        image_content_guard: ImageContentGuard,
        video_resolver: VideoProviderResolver,
        video_content_guard: VideoContentGuard,
    ) -> None:
        """Initialize the service.

        Args:
            resolver: Resolves each request to a provider, generation config,
                and whether that provider is uncensored.
            safety_guard: Crisis-phrase check. `check_request` runs
                unconditionally on every message before persona/provider
                resolution and before the image/video-intent branches;
                `wrap_stream` additionally scans the reply stream, but only
                when the resolved provider is uncensored (see SPEC.md §5).
            image_resolver: Resolves an image-generation turn to a provider
                and generation config.
            image_content_guard: Checks every image prompt against SPEC.md
                §5's hard exclusion list unconditionally, plus the
                companionship/intimate content-tier boundary when the
                resolved provider is not uncensored.
            video_resolver: Resolves a video-generation turn to a provider
                and generation config. Mirrors `image_resolver`.
            video_content_guard: Checks every video prompt the same way
                `image_content_guard` checks image prompts.
        """
        self._resolver = resolver
        self._safety_guard = safety_guard
        self._image_resolver = image_resolver
        self._image_content_guard = image_content_guard
        self._video_resolver = video_resolver
        self._video_content_guard = video_content_guard

    async def stream_response(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream an SSE-framed companion reply for the given request.

        Args:
            request: The conversation to reply to, optionally naming a
                `model_id` and, for an auto-detected generation turn, an
                `image_model_id` / `video_model_id`.

        Yields:
            SSE `data:` lines: zero or more TOKEN chunks, or exactly one
            IMAGE chunk if the latest message was detected as an image
            request, followed by exactly one DONE chunk, or one ERROR chunk
            if generation failed or a safety guard intervened.
        """
        try:
            # Crisis-phrase check runs first, on the raw message, regardless
            # of whether it ends up routed to image generation or text —
            # image generation never reaches an LLM and has no self-moderation
            # of its own to fall back on (see safety/uncensored_guard.py).
            self._safety_guard.check_request(request.messages)
        except SafetyInterventionError as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))
            return

        # Single hardcoded default persona for this increment — see
        # personas/base.py for where per-user/custom personas will plug in.
        persona = PersonaConfig()
        try:
            provider, provider_config, is_uncensored = self._resolver.resolve(
                request.model_id, persona
            )
        except ProviderError as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))
            return

        # Resolved before branching so image/video generation respects the
        # same companionship/intimate content boundary as text, instead of
        # always falling back to the uncensored backend regardless of mode.
        latest_message = request.messages[-1].content if request.messages else None

        video_prompt = detect_video_prompt(latest_message) if latest_message else None
        if video_prompt is not None:
            async for event in self._stream_video_response(
                latest_message, video_prompt, is_uncensored, request.video_model_id
            ):
                yield event
            return

        image_prompt = detect_image_prompt(latest_message) if latest_message else None
        if image_prompt is not None:
            async for event in self._stream_image_response(
                latest_message, image_prompt, is_uncensored, request.image_model_id
            ):
                yield event
            return

        if is_uncensored:
            # Uncensored providers get the non-moralizing system prompt
            # (personas/base.py) even when picked explicitly by model_id
            # rather than by persona mode.
            persona = persona.model_copy(update={"mode": "intimate"})

        try:
            stream = provider.stream_reply(request.messages, persona, provider_config)
            if is_uncensored:
                stream = self._safety_guard.wrap_stream(stream)

            async for token in stream:
                yield format_sse(StreamChunk(type=StreamChunkType.TOKEN, content=token))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except (ProviderError, SafetyInterventionError) as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))

    async def _stream_image_response(
        self, raw_message: str, prompt: str, is_uncensored: bool, model_id: str | None
    ) -> AsyncIterator[str]:
        """Generate an image for `prompt` and stream it as SSE chunks.

        Args:
            raw_message: The user's original message, checked against the
                content guard in full — `prompt` alone can be missing
                descriptor words `detect_image_prompt` strands outside the
                extracted remainder (e.g. "show me a nude picture of you"
                extracts to just "you").
            prompt: The image description extracted by
                `services/image_intent.py::detect_image_prompt`, passed to
                the provider for generation.
            is_uncensored: Whether this request resolved to an uncensored
                text provider — gates the content-tier boundary check (SPEC.md
                §5's hard exclusion list is checked regardless).
            model_id: `ImageCatalogEntry.id` chosen by the client, or `None`
                to fall back to `Settings.default_image_model_id`.

        Yields:
            One IMAGE chunk followed by one DONE chunk, or one ERROR chunk if
            the content guard blocked the prompt or generation failed.
        """
        try:
            self._image_content_guard.check_prompt(raw_message, is_uncensored)
            provider, config = self._image_resolver.resolve(model_id)
            image_url = await provider.generate_image(prompt, config)
            yield format_sse(StreamChunk(type=StreamChunkType.IMAGE, content=image_url))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except (ProviderError, SafetyInterventionError) as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))

    async def _stream_video_response(
        self, raw_message: str, prompt: str, is_uncensored: bool, model_id: str | None
    ) -> AsyncIterator[str]:
        """Generate a video for `prompt` and stream it as SSE chunks.

        Mirrors `_stream_image_response`. Args and behavior are the same,
        substituting the video resolver/guard for the image ones; `model_id`
        is a `VideoCatalogEntry.id`, or `None` for
        `Settings.default_video_model_id`.

        Yields:
            One VIDEO chunk followed by one DONE chunk, or one ERROR chunk if
            the content guard blocked the prompt or generation failed.
        """
        try:
            self._video_content_guard.check_prompt(raw_message, is_uncensored)
            provider, config = self._video_resolver.resolve(model_id)
            video_url = await provider.generate_video(prompt, config)
            yield format_sse(StreamChunk(type=StreamChunkType.VIDEO, content=video_url))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except (ProviderError, SafetyInterventionError) as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))
