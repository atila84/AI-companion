"""Resolves a chat request to a concrete provider and model.

`ProviderResolver` is the only class (besides `services/providers/registry.py`)
allowed to know the model catalog and the mode-based routing rule. Everything
else — `ChatService`, `api/routes/chat.py`, `models/chat.py`, the frontend —
only ever sees a `model_id` string, never a provider identity, preserving the
"no code outside the provider layer knows which backend is in use" seam
(`services/providers/base.py`).
"""

from src.config import ModelCatalogEntry, Settings
from src.personas.base import PersonaConfig
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.registry import build_provider


class ProviderResolver:
    """Resolves a `(model_id, persona)` pair to a provider ready to call."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the resolver.

        Args:
            settings: Application settings, supplying the catalog, routing
                defaults, and provider credentials.
        """
        self._settings = settings

    def _select_entry(self, requested_model_id: str | None, persona: PersonaConfig) -> ModelCatalogEntry:
        """Pick a catalog entry by precedence: explicit request > mode routing > default."""
        if requested_model_id is not None:
            return self._settings.catalog_entry(requested_model_id)
        if persona.mode == "intimate":
            return self._settings.catalog_entry(self._settings.intimate_mode_model_id)
        return self._settings.catalog_entry(self._settings.default_model_id)

    def resolve(
        self, requested_model_id: str | None, persona: PersonaConfig
    ) -> tuple[CompanionModelProvider, ProviderConfig, bool]:
        """Resolve a request to a ready-to-use provider and generation config.

        Args:
            requested_model_id: `ChatRequest.model_id`, if the client
                specified one.
            persona: The persona for this conversation, whose `mode` drives
                routing when `requested_model_id` is `None`.

        Returns:
            A tuple of `(provider, provider_config, is_uncensored)`.

        Raises:
            ProviderConfigError: `requested_model_id` (or a configured
                routing default) does not name an enabled catalog entry, or
                the resolved provider is missing required credentials.
        """
        entry = self._select_entry(requested_model_id, persona)
        provider = build_provider(entry.provider_id, self._settings)
        provider_config = ProviderConfig(model=entry.model)
        return provider, provider_config, entry.uncensored
