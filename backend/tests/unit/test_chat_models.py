"""Unit tests for the `ChatMessage`/`ChatRequest` request-body constraints."""

import pytest
from pydantic import ValidationError

from src.models.chat import ChatMessage, ChatRequest, ChatRole


def test_chat_message_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role=ChatRole.USER, content="")


def test_chat_message_rejects_content_over_max_length() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role=ChatRole.USER, content="a" * 8001)


def test_chat_message_accepts_content_at_max_length() -> None:
    message = ChatMessage(role=ChatRole.USER, content="a" * 8000)
    assert len(message.content) == 8000


def test_chat_request_rejects_empty_messages_list() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])


def test_chat_request_rejects_too_many_messages() -> None:
    messages = [ChatMessage(role=ChatRole.USER, content="hi") for _ in range(201)]
    with pytest.raises(ValidationError):
        ChatRequest(messages=messages)


def test_chat_request_accepts_messages_at_max_count() -> None:
    messages = [ChatMessage(role=ChatRole.USER, content="hi") for _ in range(200)]
    request = ChatRequest(messages=messages)
    assert len(request.messages) == 200
