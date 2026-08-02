"""The `CompanionModelProvider` interface.

This is the single most important architectural seam in the project (SPEC.md
§2): no code outside this module and its concrete implementations may know
which LLM backend is in use. `ChatService` depends only on
`CompanionModelProvider`; adding a second backend (e.g. a hosted open-model
API for the romantic/sexual/intimate mode) means writing a new class here,
not a new code path elsewhere.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel, Field

from src.models.chat import ChatMessage
from src.personas.base import PersonaConfig


class ProviderConfig(BaseModel):
    """Provider-agnostic generation settings for a single request.

    Fields are deliberately limited to the lowest common denominator across
    backends. A setting only one backend understands does not belong here.

    Attributes:
        model: Backend-specific model identifier.
        max_tokens: Maximum tokens to generate for the reply.
    """

    model: str
    max_tokens: int = Field(default=1024, gt=0)


class CompanionModelProvider(ABC):
    """Abstraction every LLM backend implements."""

    @abstractmethod
    def stream_reply(
        self,
        messages: list[ChatMessage],
        persona: PersonaConfig,
        config: ProviderConfig,
    ) -> AsyncIterator[str]:
        """Stream a companion reply for the given conversation.

        Args:
            messages: Full conversation history, oldest first, ending with
                the latest user turn.
            persona: The persona whose system prompt should wrap the request.
            config: Model and generation parameters for this request.

        Yields:
            Successive text fragments (not full messages) as they arrive
            from the backend.

        Raises:
            ProviderConfigError: The backend is misconfigured.
            ProviderAPIError: The backend call failed.
        """
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator for type checkers
