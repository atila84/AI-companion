"""Unit tests for `VideoContentGuard`'s enforcement of SPEC.md §5's hard exclusion list."""

import pytest

from src.services.safety.exceptions import SafetyInterventionError
from src.services.safety.video_content_guard import VideoContentGuard


@pytest.fixture
def guard() -> VideoContentGuard:
    return VideoContentGuard()


def test_allows_ordinary_prompt(guard: VideoContentGuard) -> None:
    guard.check_prompt("a sunset over the ocean, timelapse style", is_uncensored=False)


def test_blocks_minor_coded_term_combined_with_sexual_context(guard: VideoContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a naked child on a beach", is_uncensored=True)


def test_allows_minor_coded_term_without_sexual_context(guard: VideoContentGuard) -> None:
    guard.check_prompt("a child playing with a kite", is_uncensored=False)


def test_blocks_non_consent_term(guard: VideoContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a scene depicting rape", is_uncensored=True)


def test_blocks_plain_sexual_content_when_not_uncensored(guard: VideoContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a nude scene", is_uncensored=False)


def test_allows_plain_sexual_content_when_uncensored(guard: VideoContentGuard) -> None:
    guard.check_prompt("a nude scene", is_uncensored=True)
