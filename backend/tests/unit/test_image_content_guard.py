"""Unit tests for `ImageContentGuard`'s enforcement of SPEC.md §5's hard exclusion list."""

import pytest

from src.services.safety.exceptions import SafetyInterventionError
from src.services.safety.image_content_guard import ImageContentGuard


@pytest.fixture
def guard() -> ImageContentGuard:
    return ImageContentGuard()


def test_allows_ordinary_prompt(guard: ImageContentGuard) -> None:
    guard.check_prompt("a sunset over the ocean, oil painting style", is_uncensored=False)


def test_blocks_minor_coded_term_combined_with_sexual_context(guard: ImageContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a naked child on a beach", is_uncensored=True)


def test_allows_minor_coded_term_without_sexual_context(guard: ImageContentGuard) -> None:
    guard.check_prompt("a child playing with a kite", is_uncensored=False)


def test_blocks_non_consent_term(guard: ImageContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a scene depicting rape", is_uncensored=True)


def test_blocks_plain_sexual_content_when_not_uncensored(guard: ImageContentGuard) -> None:
    with pytest.raises(SafetyInterventionError):
        guard.check_prompt("a nude portrait", is_uncensored=False)


def test_allows_plain_sexual_content_when_uncensored(guard: ImageContentGuard) -> None:
    guard.check_prompt("a nude portrait", is_uncensored=True)
