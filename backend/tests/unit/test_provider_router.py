"""Unit tests for `ProviderResolver`'s routing precedence."""

import pytest

from src.config import Settings
from src.personas.base import PersonaConfig
from src.services.provider_router import ProviderResolver
from src.services.providers.exceptions import ProviderConfigError


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def resolver(settings: Settings) -> ProviderResolver:
    return ProviderResolver(settings)


def test_explicit_model_id_wins_over_persona_mode(resolver: ProviderResolver) -> None:
    persona = PersonaConfig(mode="intimate")

    _, config, is_uncensored = resolver.resolve("claude/claude-opus-5", persona)

    assert config.model == "claude-opus-5"
    assert is_uncensored is False


def test_intimate_mode_routes_to_uncensored_default_when_no_explicit_model(
    resolver: ProviderResolver,
) -> None:
    persona = PersonaConfig(mode="intimate")

    _, config, is_uncensored = resolver.resolve(None, persona)

    assert config.model == "cognitivecomputations/dolphin-mixtral-8x22b"
    assert is_uncensored is True


def test_default_model_used_when_no_explicit_model_and_not_intimate(
    resolver: ProviderResolver,
) -> None:
    persona = PersonaConfig(mode="companionship")

    _, config, is_uncensored = resolver.resolve(None, persona)

    assert config.model == "claude-opus-5"
    assert is_uncensored is False


def test_resolve_raises_for_unknown_explicit_model_id(resolver: ProviderResolver) -> None:
    persona = PersonaConfig()

    with pytest.raises(ProviderConfigError):
        resolver.resolve("nonexistent/model", persona)
