"""Unit tests for SSE framing."""

import json

from src.models.chat import StreamChunk, StreamChunkType
from src.utils.sse import format_sse


def test_format_sse_frames_a_token_chunk() -> None:
    chunk = StreamChunk(type=StreamChunkType.TOKEN, content="hi")

    formatted = format_sse(chunk)

    assert formatted.startswith("data: ")
    assert formatted.endswith("\n\n")
    payload = json.loads(formatted.removeprefix("data: ").removesuffix("\n\n"))
    assert payload == {"type": "token", "content": "hi"}


def test_format_sse_frames_a_done_chunk_with_null_content() -> None:
    chunk = StreamChunk(type=StreamChunkType.DONE)

    formatted = format_sse(chunk)

    payload = json.loads(formatted.removeprefix("data: ").removesuffix("\n\n"))
    assert payload == {"type": "done", "content": None}
