"""Resolves an image-generation request to a concrete provider and model.

Trimmed version of `services/provider_router.py::ProviderResolver`: there is
no per-request `model_id` from the client yet (no picker UI exists — see
CLAUDE.md/plan for the "no buttons" requirement), so routing is just
`requested_model_id or Settings.default_image_model_id`.
"""

from src.config import ImageCatalogEntry, Settings
from src.services.image_providers.base import ImageGenerationConfig, ImageGenerationProvider
from src.services.image_providers.registry import build_image_provider


class ImageProviderResolver:
    """Resolves a `model_id` to an image provider ready to call."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the resolver.

        Args:
            settings: Application settings, supplying the image catalog,
                routing default, and provider credentials.
        """
        self._settings = settings

    def _select_entry(self, requested_model_id: str | None) -> ImageCatalogEntry:
        model_id = requested_model_id or self._settings.default_image_model_id
        return self._settings.image_catalog_entry(model_id)

    def resolve(
        self, requested_model_id: str | None = None
    ) -> tuple[ImageGenerationProvider, ImageGenerationConfig]:
        """Resolve a request to a ready-to-use image provider and config.

        Args:
            requested_model_id: An `ImageCatalogEntry.id`, if specified.
                `None` falls back to `Settings.default_image_model_id`.

        Returns:
            A tuple of `(provider, provider_config)`.

        Raises:
            ProviderConfigError: The resolved catalog entry does not exist,
                is disabled, or its provider is missing required credentials.
        """
        entry = self._select_entry(requested_model_id)
        provider = build_image_provider(entry.provider_id, self._settings)
        config = ImageGenerationConfig(model=entry.model)
        return provider, config
