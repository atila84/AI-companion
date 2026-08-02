"""Domain and API models for a single chat turn.

These models are shared between the API layer (`api/routes/chat.py`) and the
provider layer (`services/providers/`) — they are a generic `{role, content}`
conversation shape, not tied to any one backend's request/response format, so
using them in both places does not leak provider-specific concerns into the API.
"""

from enum import Enum

from pydantic import BaseModel


class ChatRole(str, Enum):
    """Who authored a given chat message."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single turn in a conversation.

    Attributes:
        role: Who sent this message.
        content: The message text.
    """

    role: ChatRole
    content: str


class ChatRequest(BaseModel):
    """Request body for `POST /api/chat/stream`.

    There is no server-side session state in this increment (see SPEC.md §4 for
    the future persisted-session design) — the client resends the full
    conversation history on every turn, ending with the newest user message.

    Attributes:
        messages: Full conversation so far, oldest first.
        model_id: `ModelCatalogEntry.id` of the model to reply with. `None`
            defers to `services/provider_router.py::ProviderResolver`'s
            persona-mode routing, then `Settings.default_model_id`.
    """

    messages: list[ChatMessage]
    model_id: str | None = None


class StreamChunkType(str, Enum):
    """The kind of payload carried by one SSE `StreamChunk`."""

    TOKEN = "token"
    DONE = "done"
    ERROR = "error"


class StreamChunk(BaseModel):
    """One SSE `data:` payload streamed back to the client.

    Attributes:
        type: Whether this chunk carries a text fragment, marks the end of
            the stream, or reports an error.
        content: Token text for TOKEN chunks, an error message for ERROR
            chunks, and `None` for DONE chunks.
    """

    type: StreamChunkType
    content: str | None = None
