"""Shared base for providers that speak the OpenAI chat-completions wire format.

`OpenRouterProvider`, `OpenAIProvider`, and `OllamaProvider` all talk to an
OpenAI-compatible `/chat/completions` endpoint (OpenRouter and Ollama proxy or
replicate that API; OpenAI defines it). This base implements the streaming
loop and error translation once so each subclass only supplies a client.
"""

from collections.abc import AsyncIterator

import openai

from src.models.chat import ChatMessage
from src.personas.base import PersonaConfig, compose_system_prompt
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.exceptions import ProviderAPIError


class OpenAICompatibleProvider(CompanionModelProvider):
    """`CompanionModelProvider` for any OpenAI-compatible chat-completions API."""

    def __init__(self, client: openai.AsyncOpenAI) -> None:
        """Initialize the provider.

        Args:
            client: A configured `AsyncOpenAI` client, already pointed at the
                target `base_url` and carrying the relevant API key (or a
                placeholder key, for backends like Ollama that ignore it).
                Client construction happens in `api/deps.py`, not here.
        """
        self._client = client

    async def stream_reply(
        self,
        messages: list[ChatMessage],
        persona: PersonaConfig,
        config: ProviderConfig,
    ) -> AsyncIterator[str]:
        """Stream a reply from an OpenAI-compatible chat-completions endpoint.

        Args:
            messages: Full conversation history, oldest first.
            persona: The persona whose system prompt wraps this request.
            config: Model and generation parameters for this request.

        Yields:
            Successive text fragments as they arrive from the API.

        Raises:
            ProviderAPIError: The chat-completions call failed.
        """
        chat_messages = [{"role": "system", "content": compose_system_prompt(persona)}]
        chat_messages.extend({"role": m.role.value, "content": m.content} for m in messages)
        try:
            stream = await self._client.chat.completions.create(
                model=config.model,
                max_tokens=config.max_tokens,
                messages=chat_messages,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.APIError as exc:
            raise ProviderAPIError(f"{type(self).__name__} request failed: {exc}") from exc
