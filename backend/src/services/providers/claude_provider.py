"""`CompanionModelProvider` implementation backed by the Anthropic Claude API."""

from collections.abc import AsyncIterator

import anthropic

from src.models.chat import ChatMessage
from src.personas.base import PersonaConfig, compose_system_prompt
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.exceptions import ProviderAPIError


class ClaudeProvider(CompanionModelProvider):
    """Streams companion replies from the Anthropic Claude API."""

    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        """Initialize the provider.

        Args:
            client: A configured `AsyncAnthropic` client. API key resolution
                happens where the client is constructed (`api/deps.py`), not
                here — this class only knows how to talk to an already-built
                client.
        """
        self._client = client

    async def stream_reply(
        self,
        messages: list[ChatMessage],
        persona: PersonaConfig,
        config: ProviderConfig,
    ) -> AsyncIterator[str]:
        """Stream a reply from Claude.

        Args:
            messages: Full conversation history, oldest first.
            persona: The persona whose system prompt wraps this request.
            config: Model and generation parameters for this request.

        Yields:
            Successive text fragments as they arrive from the API.

        Raises:
            ProviderAPIError: The Anthropic API call failed.
        """
        anthropic_messages = [{"role": m.role.value, "content": m.content} for m in messages]
        system_prompt = compose_system_prompt(persona)
        try:
            async with self._client.messages.stream(
                model=config.model,
                max_tokens=config.max_tokens,
                system=system_prompt,
                messages=anthropic_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIError as exc:
            raise ProviderAPIError(f"Claude API request failed: {exc}") from exc
