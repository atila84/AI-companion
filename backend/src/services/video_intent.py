"""Detects whether a chat message is asking for a generated video.

Mirrors `services/image_intent.py::detect_image_prompt`: there is deliberately
no explicit "generate video" button or endpoint — the backend infers intent
from the message text itself. Same keyword/regex placeholder spirit as
`services/safety/uncensored_guard.py`.

Unlike image intent, there is no "draw me"-style bare-verb trigger here —
"draw"/"sketch" strongly imply a still image, so video intent only fires when
the message names a video noun explicitly (`video`, `clip`, `animation`),
keeping this detector from swallowing image requests that happen to use one
of the same generate/create/make/send/show verbs.
"""

import re
from typing import Final

_VIDEO_NOUN = r"(?:videos?|clips?|animations?)"

_TRIGGER_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\banimate(?: me)?\b\s*(.*)",
        rf"\bgenerate(?:\s+me)?\b[^.!?\n]*?\b{_VIDEO_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bcreate(?:\s+me)?\b[^.!?\n]*?\b{_VIDEO_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bmake(?:\s+me)?\b[^.!?\n]*?\b{_VIDEO_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bsend(?:\s+me)?\b[^.!?\n]*?\b{_VIDEO_NOUN}\b(?:\s+of\s*)?(.*)",
        rf"\bshow(?:\s+me)?\b[^.!?\n]*?\b{_VIDEO_NOUN}\b(?:\s+of\s*)?(.*)",
    )
)


def detect_video_prompt(text: str) -> str | None:
    """Detect video-generation intent in a chat message and extract its prompt.

    Args:
        text: The chat message to inspect.

    Returns:
        The extracted video prompt if `text` matches a trigger phrase (the
        text after the trigger, or the full message if the trigger leaves
        nothing usable after it), or `None` if no video intent is detected.
    """
    for pattern in _TRIGGER_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        remainder = match.group(1).strip(" .!?")
        return remainder if remainder else text.strip()
    return None
