"""Orchestrates persona wrapping and provider streaming for one chat turn."""

from collections.abc import AsyncIterator

from src.models.chat import ChatRequest, StreamChunk, StreamChunkType
from src.personas.base import PersonaConfig
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.exceptions import ProviderError
from src.utils.sse import format_sse


class ChatService:
    """Turns a `ChatRequest` into a stream of SSE-framed `StreamChunk`s."""

    def __init__(self, provider: CompanionModelProvider, provider_config: ProviderConfig) -> None:
        """Initialize the service.

        Args:
            provider: The LLM backend to generate replies with.
            provider_config: Model/generation settings passed to the provider
                on every request.
        """
        self._provider = provider
        self._provider_config = provider_config

    async def stream_response(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream an SSE-framed companion reply for the given request.

        Args:
            request: The conversation to reply to.

        Yields:
            SSE `data:` lines: zero or more TOKEN chunks, followed by exactly
            one DONE chunk, or one ERROR chunk if generation failed.
        """
        # Single hardcoded default persona for this increment — see
        # personas/base.py for where per-user/custom personas will plug in.
        persona = PersonaConfig()
        try:
            async for token in self._provider.stream_reply(
                request.messages, persona, self._provider_config
            ):
                yield format_sse(StreamChunk(type=StreamChunkType.TOKEN, content=token))
            yield format_sse(StreamChunk(type=StreamChunkType.DONE))
        except ProviderError as exc:
            yield format_sse(StreamChunk(type=StreamChunkType.ERROR, content=str(exc)))

        # Future hook: a moderation/crisis-detection layer (SPEC.md §5) would
        # wrap this loop — inspecting `request.messages` before generation
        # and/or each yielded token before it reaches the client — rather
        # than being built here now.
