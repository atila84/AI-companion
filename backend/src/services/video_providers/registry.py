"""Factory for turning a `VideoProviderId` into a `VideoGenerationProvider`.

Mirrors `services/image_providers/registry.py::build_image_provider`: a
deliberately dumb dict lookup, not a plugin-discovery mechanism. Adding a new
video backend means one new `VideoGenerationProvider` subclass plus one entry
here.
"""

from collections.abc import Callable
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

import openai

from src.services.providers.exceptions import ProviderConfigError
from src.services.video_providers.base import VideoGenerationProvider
from src.services.video_providers.comfyui_provider import ComfyUIVideoProvider
from src.services.video_providers.openai_video_provider import OpenAIVideoProvider

if TYPE_CHECKING:
    from src.config import Settings


class VideoProviderId(str, Enum):
    """Identifies which `VideoGenerationProvider` implementation to use."""

    COMFYUI = "comfyui"
    OPENAI = "openai"


@lru_cache
def _openai_client(api_key: str) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=api_key)


def _build_comfyui(settings: "Settings") -> VideoGenerationProvider:
    if not settings.comfyui_base_url:
        raise ProviderConfigError("COMFYUI_BASE_URL is not set.")
    return ComfyUIVideoProvider(settings.comfyui_base_url)


def _build_openai_video(settings: "Settings") -> VideoGenerationProvider:
    if not settings.openai_api_key:
        raise ProviderConfigError("OPENAI_API_KEY is not set.")
    return OpenAIVideoProvider(_openai_client(settings.openai_api_key))


_VIDEO_PROVIDER_FACTORIES: dict[VideoProviderId, "Callable[[Settings], VideoGenerationProvider]"] = {
    VideoProviderId.COMFYUI: _build_comfyui,
    VideoProviderId.OPENAI: _build_openai_video,
}


def build_video_provider(provider_id: VideoProviderId, settings: "Settings") -> VideoGenerationProvider:
    """Build a `VideoGenerationProvider` for `provider_id`.

    Args:
        provider_id: Which provider implementation to build.
        settings: Application settings, supplying credentials/endpoints.

    Returns:
        A ready-to-use `VideoGenerationProvider`.

    Raises:
        ProviderConfigError: `provider_id` is unknown, or its required
            credentials are not configured.
    """
    factory = _VIDEO_PROVIDER_FACTORIES.get(provider_id)
    if factory is None:
        raise ProviderConfigError(f"Unknown video provider: {provider_id!r}")
    return factory(settings)
