"""Safety check for every video-generation prompt, in two tiers.

Mirrors `services/safety/image_content_guard.py::ImageContentGuard` — same
two-tier structure (SPEC.md §5's hard exclusion list, checked unconditionally;
the companionship/intimate content-tier boundary, gated on `is_uncensored`),
same keyword-based placeholder status, and the same reasoning for why this
runs on every prompt regardless of which backend renders it: video generation
has no LLM in the loop to apply contextual judgment either.
"""

from typing import Final

from src.services.safety.exceptions import SafetyInterventionError

MINOR_CODED_TERMS: Final[tuple[str, ...]] = (
    "child",
    "kid",
    "kids",
    "minor",
    "loli",
    "shota",
    "underage",
    "teen",
    "toddler",
    "little girl",
    "little boy",
)

SEXUAL_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "nude",
    "naked",
    "sex",
    "sexual",
    "nsfw",
    "explicit",
    "porn",
)

NON_CONSENT_TERMS: Final[tuple[str, ...]] = (
    "rape",
    "raping",
    "non-consensual",
    "nonconsensual",
    "without consent",
    "against her will",
    "against his will",
    "forced sex",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


class VideoContentGuard:
    """Keyword check enforcing SPEC.md §5's hard exclusion list on video prompts."""

    def check_prompt(self, prompt: str, is_uncensored: bool) -> None:
        """Check a video-generation prompt against both safety tiers.

        Args:
            prompt: The user's message to check. Should be the raw message
                text rather than a post-extraction remainder — extraction can
                strand descriptor words outside what it returns (see
                `ChatService._stream_video_response`), which would let
                explicit content slip past a check of the extracted text
                alone.
            is_uncensored: Whether this request resolved to an uncensored
                text provider. Gates the content-tier check only — the hard
                exclusion list below is checked regardless.

        Raises:
            SafetyInterventionError: The prompt combines minor-coded language
                with sexual context, contains a non-consent term (both
                checked unconditionally), or requests plain sexual content
                while `is_uncensored` is False (this mode's content-tier
                boundary).
        """
        lowered = prompt.lower()
        if _contains_any(lowered, MINOR_CODED_TERMS) and _contains_any(lowered, SEXUAL_CONTEXT_TERMS):
            raise SafetyInterventionError("This video request isn't something I can generate.")
        if _contains_any(lowered, NON_CONSENT_TERMS):
            raise SafetyInterventionError("This video request isn't something I can generate.")
        if not is_uncensored and _contains_any(lowered, SEXUAL_CONTEXT_TERMS):
            raise SafetyInterventionError("This video request isn't something I can generate in this mode.")
