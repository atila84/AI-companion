"""Unit tests for fail-fast settings loading."""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_settings_raises_without_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_picks_up_anthropic_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.anthropic_api_key == "sk-ant-test-key"
    assert settings.claude_model == "claude-opus-5"
