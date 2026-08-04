"""Unit tests for the provider factory/registry."""

import pytest

from src.config import Settings
from src.services.providers.claude_provider import ClaudeProvider
from src.services.providers.exceptions import ProviderConfigError
from src.services.providers.ollama_provider import OllamaProvider
from src.services.providers.openai_provider import OpenAIProvider
from src.services.providers.openrouter_provider import OpenRouterProvider
from src.services.providers.registry import ProviderId, build_provider


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_build_provider_dispatches_claude(settings: Settings) -> None:
    assert isinstance(build_provider(ProviderId.CLAUDE, settings), ClaudeProvider)


def test_build_provider_raises_for_ollama_without_base_url(settings: Settings) -> None:
    with pytest.raises(ProviderConfigError):
        build_provider(ProviderId.OLLAMA, settings)


def test_build_provider_dispatches_ollama_without_api_key_once_base_url_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert isinstance(build_provider(ProviderId.OLLAMA, settings), OllamaProvider)


def test_build_provider_raises_for_openrouter_without_key(settings: Settings) -> None:
    with pytest.raises(ProviderConfigError):
        build_provider(ProviderId.OPENROUTER, settings)


def test_build_provider_raises_for_openai_without_key(settings: Settings) -> None:
    with pytest.raises(ProviderConfigError):
        build_provider(ProviderId.OPENAI, settings)


def test_build_provider_dispatches_openrouter_once_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert isinstance(build_provider(ProviderId.OPENROUTER, settings), OpenRouterProvider)


def test_build_provider_dispatches_openai_once_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert isinstance(build_provider(ProviderId.OPENAI, settings), OpenAIProvider)
