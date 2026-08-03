"""Safety check for every image-generation prompt, in two tiers.

Two independent checks live here, mirroring SPEC.md §5's structure:

1. The hard content exclusion list (minor-coded + sexual combinations,
   non-consent terms) — "enforced at the system/application level, above
   every persona and every backend, non-negotiable" — checked unconditionally,
   regardless of mode.
2. The companionship/intimate content-tier boundary (SPEC.md §5 "Content
   tiers") — plain sexual content is only permitted when the resolved text
   provider for this request is uncensored (`is_uncensored=True`, i.e. the
   intimate tier); otherwise it's blocked the same way Claude would decline
   it in text.

Unlike `uncensored_guard.py::UncensoredSafetyGuard`, which only wraps
`uncensored=True` chat providers, tier 1 here runs on **every** image prompt
regardless of which backend generates it — image generation has no LLM in
the loop to apply the kind of contextual judgment Claude applies to text, so
the application-layer check has to do all the work.

This is a keyword-based placeholder, same spirit as `uncensored_guard.py`:
easy to extend, not a complete solution. In particular, real-identifiable-
person detection is not implemented by keyword matching (that would need a
name/face-recognition pass) — this is a known, explicit gap, not something
this module claims to handle.
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


class ImageContentGuard:
    """Keyword check enforcing SPEC.md §5's hard exclusion list on image prompts."""

    def check_prompt(self, prompt: str, is_uncensored: bool) -> None:
        """Check an image-generation prompt against both safety tiers.

        Args:
            prompt: The user's message to check. Should be the raw message
                text rather than a post-extraction remainder — extraction can
                strand descriptor words outside what it returns (see
                `ChatService._stream_image_response`), which would let
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
            raise SafetyInterventionError("This image request isn't something I can generate.")
        if _contains_any(lowered, NON_CONSENT_TERMS):
            raise SafetyInterventionError("This image request isn't something I can generate.")
        if not is_uncensored and _contains_any(lowered, SEXUAL_CONTEXT_TERMS):
            raise SafetyInterventionError("This image request isn't something I can generate in this mode.")
