"""Factory for turning an `ImageProviderId` into an `ImageGenerationProvider`.

Mirrors `services/providers/registry.py::build_provider`: a deliberately dumb
dict lookup, not a plugin-discovery mechanism. Adding a new image backend
means one new `ImageGenerationProvider` subclass plus one entry here.
"""

from collections.abc import Callable
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

import openai

from src.services.image_providers.automatic1111_provider import Automatic1111Provider
from src.services.image_providers.base import ImageGenerationProvider
from src.services.image_providers.openai_image_provider import OpenAIImageProvider
from src.services.image_providers.pollinations_provider import PollinationsProvider
from src.services.providers.exceptions import ProviderConfigError

if TYPE_CHECKING:
    from src.config import Settings


class ImageProviderId(str, Enum):
    """Identifies which `ImageGenerationProvider` implementation to use."""

    POLLINATIONS = "pollinations"
    AUTOMATIC1111 = "automatic1111"
    OPENAI = "openai"


@lru_cache
def _openai_client(api_key: str) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=api_key)


def _build_pollinations(settings: "Settings") -> ImageGenerationProvider:
    return PollinationsProvider()


def _build_automatic1111(settings: "Settings") -> ImageGenerationProvider:
    if not settings.automatic1111_base_url:
        raise ProviderConfigError("AUTOMATIC1111_BASE_URL is not set.")
    return Automatic1111Provider(settings.automatic1111_base_url)


def _build_openai_image(settings: "Settings") -> ImageGenerationProvider:
    if not settings.openai_api_key:
        raise ProviderConfigError("OPENAI_API_KEY is not set.")
    return OpenAIImageProvider(_openai_client(settings.openai_api_key))


_IMAGE_PROVIDER_FACTORIES: dict[ImageProviderId, "Callable[[Settings], ImageGenerationProvider]"] = {
    ImageProviderId.POLLINATIONS: _build_pollinations,
    ImageProviderId.AUTOMATIC1111: _build_automatic1111,
    ImageProviderId.OPENAI: _build_openai_image,
}


def build_image_provider(provider_id: ImageProviderId, settings: "Settings") -> ImageGenerationProvider:
    """Build an `ImageGenerationProvider` for `provider_id`.

    Args:
        provider_id: Which provider implementation to build.
        settings: Application settings, supplying credentials/endpoints.

    Returns:
        A ready-to-use `ImageGenerationProvider`.

    Raises:
        ProviderConfigError: `provider_id` is unknown, or its required
            credentials are not configured.
    """
    factory = _IMAGE_PROVIDER_FACTORIES.get(provider_id)
    if factory is None:
        raise ProviderConfigError(f"Unknown image provider: {provider_id!r}")
    return factory(settings)
