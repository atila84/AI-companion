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
from src.utils.sse import format_sse


class ChatService:
    """Turns a `ChatRequest` into a stream of SSE-framed `StreamChunk`s."""

    def __init__(
        self,
        resolver: ProviderResolver,
        safety_guard: UncensoredSafetyGuard,
        image_resolver: ImageProviderResolver,
        image_content_guard: ImageContentGuard,
    ) -> None:
        """Initialize the service.

        Args:
            resolver: Resolves each request to a provider, generation config,
                and whether that provider is uncensored.
            safety_guard: Independent safety check applied only when the
                resolved provider is uncensored (see SPEC.md §5).
            image_resolver: Resolves an image-generation turn to a provider
                and generation config.
            image_content_guard: Independent, unconditional check of every
                image prompt against SPEC.md §5's hard exclusion list.
        """
        self._resolver = resolver
        self._safety_guard = safety_guard
        self._image_resolver = image_resolver
        self._image_content_guard = image_content_guard

    async def stream_response(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream an SSE-framed companion reply for the given request.

        Args:
            request: The conversation to reply to, optionally naming a
                `model_id`.

        Yields:
            SSE `data:` lines: zero or more TOKEN chunks, or exactly one
            IMAGE chunk if the latest message was detected as an image
            request, followed by exactly one DONE chunk, or one ERROR chunk
            if generation failed or a safety guard intervened.
        """
        image_prompt = detect_image_prompt(request.messages[-1].content) if request.messages else None
        if image_prompt is not None:
            async for event in self._stream_image_response(image_prompt):
                yield event
            return

        # Single hardcoded default persona for this increment — see
        # personas/base.py for where per-user/custom personas will plug in.
        persona = PersonaConfig()
        try:
            provider, provider_config, is_uncensored = self._resolver.resolve(
                request.model_id, persona
            )
            if is_uncensored:
                self._safety_guard.check_request(request.messages)
                # Uncensored providers get the non-moralizing system prompt
                # (personas/base.py) even when picked explicitly by model_id
                # rather than by persona mode.
                persona = persona.model_copy(update={"mode": "intimate"})

            stream = provider.stream_reply(request.messages, persona, provider_config)
            if is_uncensored:
                stream = self._safety_guard.wrap_stream(stream)

            async for token in stream:
                yield format_sse(StreamChunk(type=StreamChunkType.TOKEN, content=token))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except (ProviderError, SafetyInterventionError) as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))

    async def _stream_image_response(self, prompt: str) -> AsyncIterator[str]:
        """Generate an image for `prompt` and stream it as SSE chunks.

        Args:
            prompt: The image description extracted by
                `services/image_intent.py::detect_image_prompt`.

        Yields:
            One IMAGE chunk followed by one DONE chunk, or one ERROR chunk if
            the content guard blocked the prompt or generation failed.
        """
        try:
            self._image_content_guard.check_prompt(prompt)
            provider, config = self._image_resolver.resolve()
            image_url = await provider.generate_image(prompt, config)
            yield format_sse(StreamChunk(type=StreamChunkType.IMAGE, content=image_url))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except (ProviderError, SafetyInterventionError) as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))
