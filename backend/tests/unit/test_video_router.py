"""Unit tests for `VideoProviderResolver`'s routing."""

import pytest

from src.config import Settings
from src.services.providers.exceptions import ProviderConfigError
from src.services.video_providers.comfyui_provider import ComfyUIVideoProvider
from src.services.video_router import VideoProviderResolver


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("COMFYUI_BASE_URL", "http://localhost:8188")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def resolver(settings: Settings) -> VideoProviderResolver:
    return VideoProviderResolver(settings)


def test_default_routing_picks_comfyui_when_configured(resolver: VideoProviderResolver) -> None:
    provider, config = resolver.resolve()

    assert isinstance(provider, ComfyUIVideoProvider)
    assert config.model == "wan2.2"


def test_explicit_model_id_is_honored(resolver: VideoProviderResolver) -> None:
    provider, _ = resolver.resolve("comfyui/wan2.2")

    assert isinstance(provider, ComfyUIVideoProvider)


def test_resolve_raises_for_unknown_model_id(resolver: VideoProviderResolver) -> None:
    with pytest.raises(ProviderConfigError):
        resolver.resolve("nonexistent/model")


def test_resolve_raises_for_disabled_provider(resolver: VideoProviderResolver) -> None:
    with pytest.raises(ProviderConfigError):
        resolver.resolve("openai/sora-2")


def test_default_routing_raises_when_comfyui_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("COMFYUI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    with pytest.raises(ProviderConfigError):
        VideoProviderResolver(settings).resolve()
