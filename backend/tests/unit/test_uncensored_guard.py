"""Unit tests for `UncensoredSafetyGuard`, independent of any provider."""

from collections.abc import AsyncIterator

import pytest

from src.models.chat import ChatMessage, ChatRole
from src.services.safety.exceptions import SafetyInterventionError
from src.services.safety.uncensored_guard import UncensoredSafetyGuard, _trim_to_trailing_context


async def _tokens(*parts: str) -> AsyncIterator[str]:
    for part in parts:
        yield part


@pytest.fixture
def guard() -> UncensoredSafetyGuard:
    return UncensoredSafetyGuard()


def test_check_request_allows_benign_message(guard: UncensoredSafetyGuard) -> None:
    guard.check_request([ChatMessage(role=ChatRole.USER, content="tell me a story")])


def test_check_request_blocks_trigger_phrase(guard: UncensoredSafetyGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_request([ChatMessage(role=ChatRole.USER, content="I want to kill myself")])


def test_check_request_allows_empty_history(guard: UncensoredSafetyGuard) -> None:
    guard.check_request([])


async def test_wrap_stream_passes_through_benign_tokens(guard: UncensoredSafetyGuard) -> None:
    received = [token async for token in guard.wrap_stream(_tokens("Once", " upon", " a time"))]

    assert received == ["Once", " upon", " a time"]


async def test_wrap_stream_raises_when_trigger_phrase_assembles_across_tokens(
    guard: UncensoredSafetyGuard,
) -> None:
    with pytest.raises(SafetyInterventionError):
        async for _ in guard.wrap_stream(_tokens("I want to ", "end my life")):
            pass


async def test_wrap_stream_raises_when_trigger_phrase_assembles_across_many_single_char_tokens(
    guard: UncensoredSafetyGuard,
) -> None:
    # A long benign prefix streamed one character at a time, followed by a
    # trigger phrase split across a token boundary. Finding 6 regression:
    # this must still be caught by a bounded trailing window, not require
    # retaining the whole accumulated reply.
    prefix = list("a" * 5000)
    with pytest.raises(SafetyInterventionError):
        async for _ in guard.wrap_stream(_tokens(*prefix, "end my ", "life")):
            pass


def test_trim_to_trailing_context_keeps_short_buffers_unchanged() -> None:
    assert _trim_to_trailing_context("hello", max_len=10) == "hello"


def test_trim_to_trailing_context_caps_long_buffers_to_max_len_minus_one() -> None:
    trimmed = _trim_to_trailing_context("a" * 1000, max_len=11)

    assert trimmed == "a" * 10
