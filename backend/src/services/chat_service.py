"""Orchestrates persona wrapping, provider resolution, and streaming for one chat turn."""

from collections.abc import AsyncIterator

from src.models.chat import ChatRequest, StreamChunk, StreamChunkType
from src.personas.base import PersonaConfig
from src.services.provider_router import ProviderResolver
from src.services.providers.exceptions import ProviderError
from src.services.safety.exceptions import SafetyInterventionError
from src.services.safety.uncensored_guard import UncensoredSafetyGuard
from src.utils.sse import format_sse


class ChatService:
    """Turns a `ChatRequest` into a stream of SSE-framed `StreamChunk`s."""

    def __init__(self, resolver: ProviderResolver, safety_guard: UncensoredSafetyGuard) -> None:
        """Initialize the service.

        Args:
            resolver: Resolves each request to a provider, generation config,
                and whether that provider is uncensored.
            safety_guard: Independent safety check applied only when the
                resolved provider is uncensored (see SPEC.md §5).
        """
        self._resolver = resolver
        self._safety_guard = safety_guard

    async def stream_response(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream an SSE-framed companion reply for the given request.

        Args:
            request: The conversation to reply to, optionally naming a
                `model_id`.

        Yields:
            SSE `data:` lines: zero or more TOKEN chunks, followed by exactly
            one DONE chunk, or one ERROR chunk if generation failed or the
            safety guard intervened.
        """
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
