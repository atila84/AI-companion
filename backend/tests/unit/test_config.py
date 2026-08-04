"""Unit tests for fail-fast settings loading and the model catalog."""

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.services.providers.exceptions import ProviderConfigError


def test_settings_raises_without_anthropic_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_picks_up_anthropic_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.anthropic_api_key == "sk-ant-test-key"
    assert settings.claude_model == "claude-opus-5"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_enabled_catalog_excludes_providers_without_credentials(settings: Settings) -> None:
    enabled_provider_ids = {entry.provider_id for entry in settings.enabled_catalog()}

    assert "claude" in enabled_provider_ids
    assert "openrouter" not in enabled_provider_ids
    assert "openai" not in enabled_provider_ids
    # Ollama needs no API key, but a local server isn't assumed to be
    # running -- opt in explicitly via OLLAMA_BASE_URL, like automatic1111.
    assert "ollama" not in enabled_provider_ids


def test_enabled_catalog_includes_ollama_once_base_url_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    enabled_provider_ids = {entry.provider_id for entry in settings.enabled_catalog()}

    assert "ollama" in enabled_provider_ids


def test_enabled_catalog_includes_openrouter_once_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    enabled_provider_ids = {entry.provider_id for entry in settings.enabled_catalog()}

    assert "openrouter" in enabled_provider_ids


def test_catalog_entry_returns_known_enabled_entry(settings: Settings) -> None:
    entry = settings.catalog_entry("claude/claude-opus-5")

    assert entry.model == "claude-opus-5"


def test_catalog_entry_raises_for_unknown_id(settings: Settings) -> None:
    with pytest.raises(ProviderConfigError):
        settings.catalog_entry("nonexistent/model")


def test_catalog_entry_raises_for_disabled_provider(settings: Settings) -> None:
    # OPENROUTER_API_KEY is unset in this fixture, so this entry is disabled.
    with pytest.raises(ProviderConfigError):
        settings.catalog_entry("openrouter/dolphin-mixtral-8x22b")
