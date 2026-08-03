"""Unit tests for `ImageProviderResolver`'s routing."""

import pytest

from src.config import Settings
from src.services.image_providers.pollinations_provider import PollinationsProvider
from src.services.image_router import ImageProviderResolver
from src.services.providers.exceptions import ProviderConfigError


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("AUTOMATIC1111_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def resolver(settings: Settings) -> ImageProviderResolver:
    return ImageProviderResolver(settings)


def test_default_routing_picks_pollinations_out_of_the_box(resolver: ImageProviderResolver) -> None:
    provider, config = resolver.resolve()

    assert isinstance(provider, PollinationsProvider)
    assert config.model == "flux"


def test_explicit_model_id_is_honored(resolver: ImageProviderResolver) -> None:
    provider, _ = resolver.resolve("pollinations/flux")

    assert isinstance(provider, PollinationsProvider)


def test_resolve_raises_for_unknown_model_id(resolver: ImageProviderResolver) -> None:
    with pytest.raises(ProviderConfigError):
        resolver.resolve("nonexistent/model")


def test_resolve_raises_for_disabled_provider(resolver: ImageProviderResolver) -> None:
    with pytest.raises(ProviderConfigError):
        resolver.resolve("automatic1111/sdxl")
