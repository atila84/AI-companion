"""Independent, unconditional safety check for every image-generation prompt.

Unlike `uncensored_guard.py::UncensoredSafetyGuard`, which only wraps
`uncensored=True` chat providers, this guard runs on **every** image prompt
regardless of which backend generates it. SPEC.md §5's hard content exclusion
list (no non-consent themes, no minor-coded scenarios, no real identifiable
people) is "enforced at the system/application level, above every persona and
every backend, non-negotiable" — and image generation has no LLM in the loop
to apply the kind of contextual judgment Claude applies to text, so the
application-layer check has to do all the work here.

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

    def check_prompt(self, prompt: str) -> None:
        """Check an image-generation prompt against the hard exclusion list.

        Args:
            prompt: The extracted image prompt about to be sent to a
                provider.

        Raises:
            SafetyInterventionError: The prompt combines minor-coded language
                with sexual context, or contains a non-consent term.
        """
        lowered = prompt.lower()
        if _contains_any(lowered, MINOR_CODED_TERMS) and _contains_any(lowered, SEXUAL_CONTEXT_TERMS):
            raise SafetyInterventionError("This image request isn't something I can generate.")
        if _contains_any(lowered, NON_CONSENT_TERMS):
            raise SafetyInterventionError("This image request isn't something I can generate.")
