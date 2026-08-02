"""Independent safety check for uncensored providers.

Claude relies on its own built-in safety tuning and LLM judgment for
crisis-adjacent content (SPEC.md §5). Uncensored providers (`uncensored=True`
catalog entries) have no such built-in filtering, so any conversation routed
to one is additionally checked here — independently of persona and of
whichever provider is in use. This is a keyword-based placeholder for the
classifier-backed version SPEC.md §5 describes as future work; the trigger
list is intentionally small and easy to extend without touching call sites.
"""

from collections.abc import AsyncIterator
from typing import Final

from src.models.chat import ChatMessage
from src.services.safety.exceptions import SafetyInterventionError

CRISIS_TRIGGER_PHRASES: Final[tuple[str, ...]] = (
    "kill myself",
    "end my life",
    "want to die",
    "suicide",
    "self-harm",
    "hurt myself",
)


def _contains_trigger_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in CRISIS_TRIGGER_PHRASES)


class UncensoredSafetyGuard:
    """Keyword check wrapping requests/replies routed to uncensored providers."""

    def check_request(self, messages: list[ChatMessage]) -> None:
        """Check incoming conversation history before generation starts.

        Args:
            messages: Full conversation history, oldest first.

        Raises:
            SafetyInterventionError: A crisis trigger phrase was found in the
                latest user message.
        """
        if messages and _contains_trigger_phrase(messages[-1].content):
            raise SafetyInterventionError(
                "This conversation needs a different kind of support right now."
            )

    async def wrap_stream(self, tokens: AsyncIterator[str]) -> AsyncIterator[str]:
        """Scan a token stream for crisis-adjacent content as it arrives.

        Args:
            tokens: The raw text fragments yielded by the provider.

        Yields:
            The same fragments, unmodified, until (if ever) a trigger phrase
            is detected in the accumulated reply.

        Raises:
            SafetyInterventionError: A crisis trigger phrase was found in the
                model's reply.
        """
        buffer = ""
        async for token in tokens:
            buffer += token
            if _contains_trigger_phrase(buffer):
                raise SafetyInterventionError(
                    "This conversation needs a different kind of support right now."
                )
            yield token
