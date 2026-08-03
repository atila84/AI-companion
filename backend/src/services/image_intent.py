"""Detects whether a chat message is asking for a generated image.

There is deliberately no explicit "generate image" button or endpoint (see
the image-generation plan) — the backend infers intent from the message text
itself. This is a keyword/regex placeholder in the same spirit as
`services/safety/uncensored_guard.py`: a small, easy-to-extend trigger list
standing in for a future intent classifier, not a complete natural-language
understanding of every possible phrasing.
"""

import re
from typing import Final

_IMAGE_NOUN = r"(?:images?|pictures?|photos?|pics?)"

_TRIGGER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:draw|sketch)(?: me)?\b\s*(.*)",
        # Verb followed by the image noun somewhere later in the same
        # sentence (bounded by [^.!?\n]) — any adjectives/articles/nothing
        # may sit in between, e.g. "generate porno picture", "generate an
        # image of", "show me a picture".
        rf"\bgenerate(?:\s+me)?\b[^.!?\n]*?\b{_IMAGE_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bcreate(?:\s+me)?\b[^.!?\n]*?\b{_IMAGE_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bmake(?:\s+me)?\b[^.!?\n]*?\b{_IMAGE_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bsend(?:\s+me)?\b[^.!?\n]*?\b{_IMAGE_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bshow(?:\s+me)?\b[^.!?\n]*?\b{_IMAGE_NOUN}\b(?:\s+of\s*)?(.*)",
    )
)


def detect_image_prompt(text: str) -> str | None:
    """Detect image-generation intent in a chat message and extract its prompt.

    Args:
        text: The chat message to inspect.

    Returns:
        The extracted image prompt if `text` matches a trigger phrase (the
        text after the trigger, or the full message if the trigger leaves
        nothing usable after it), or `None` if no image intent is detected.
    """
    for pattern in _TRIGGER_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        remainder = match.group(1).strip(" .!?")
        return remainder if remainder else text.strip()
    return None
