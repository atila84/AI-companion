"""Resolves a video-generation request to a concrete provider and model.

Trimmed version of `services/provider_router.py::ProviderResolver`, mirroring
`services/image_router.py::ImageProviderResolver`: there is no per-request
`model_id` from the client yet (no picker UI exists), so routing is just
`requested_model_id or Settings.default_video_model_id`.
"""

from src.config import Settings, VideoCatalogEntry
from src.services.video_providers.base import VideoGenerationConfig, VideoGenerationProvider
from src.services.video_providers.registry import build_video_provider


class VideoProviderResolver:
    """Resolves a `model_id` to a video provider ready to call."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the resolver.

        Args:
            settings: Application settings, supplying the video catalog,
                routing default, and provider credentials.
        """
        self._settings = settings

    def _select_entry(self, requested_model_id: str | None) -> VideoCatalogEntry:
        model_id = requested_model_id or self._settings.default_video_model_id
        return self._settings.video_catalog_entry(model_id)

    def resolve(
        self, requested_model_id: str | None = None
    ) -> tuple[VideoGenerationProvider, VideoGenerationConfig]:
        """Resolve a request to a ready-to-use video provider and config.

        Args:
            requested_model_id: A `VideoCatalogEntry.id`, if specified.
                `None` falls back to `Settings.default_video_model_id`.

        Returns:
            A tuple of `(provider, provider_config)`.

        Raises:
            ProviderConfigError: The resolved catalog entry does not exist,
                is disabled, or its provider is missing required credentials.
        """
        entry = self._select_entry(requested_model_id)
        provider = build_video_provider(entry.provider_id, self._settings)
        config = VideoGenerationConfig(model=entry.model)
        return provider, config
