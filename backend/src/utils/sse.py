"""Server-Sent Events framing helpers."""

from src.models.chat import StreamChunk


def format_sse(chunk: StreamChunk) -> str:
    """Format a `StreamChunk` as one SSE `data:` event.

    Args:
        chunk: The chunk to send.

    Returns:
        A string of the form `"data: <json>\\n\\n"`, ready to be written
        directly to an SSE response body.
    """
    return f"data: {chunk.model_dump_json()}\n\n"
