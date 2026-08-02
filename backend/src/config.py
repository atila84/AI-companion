"""Application configuration.

Settings are loaded from environment variables / a local `.env` file. Construction
deliberately fails fast (a `pydantic.ValidationError`) when `ANTHROPIC_API_KEY` is
unset, rather than allowing the app to start and fail obscurely on the first chat
request — see `src/main.py` for how this is surfaced as a clear startup error.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.services.providers.exceptions import ProviderConfigError
from src.services.providers.registry import ProviderId


class ModelCatalogEntry(BaseModel):
    """One selectable (provider, model) pair exposed to clients.

    Attributes:
        id: Stable identifier the client sends as `ChatRequest.model_id`
            (e.g. `"openrouter/dolphin-mixtral-8x22b"`).
        provider_id: Which provider factory handles this entry.
        model: Backend-specific model string passed through to the SDK call.
        display_name: Shown in the frontend model picker.
        cost_tier: Whether calling this model costs money.
        uncensored: Whether this model has no built-in content filtering.
            Drives the independent safety-layer wrap in `ChatService`.
        enabled: Allows disabling a catalog entry without deleting it.
    """

    id: str
    provider_id: ProviderId
    model: str
    display_name: str
    cost_tier: Literal["free", "paid"]
    uncensored: bool = False
    enabled: bool = True


def _default_catalog() -> list[ModelCatalogEntry]:
    """The initial hardcoded model catalog.

    A DB-backed, admin-editable catalog is future work — this increment
    ships a fixed list covering each requested category (paid, free,
    uncensored) via OpenRouter, plus the existing Claude entry.
    """
    return [
        ModelCatalogEntry(
            id="claude/claude-opus-5",
            provider_id=ProviderId.CLAUDE,
            model="claude-opus-5",
            display_name="Claude Opus 5",
            cost_tier="paid",
        ),
        ModelCatalogEntry(
            id="openrouter/llama-3.1-8b-instruct-free",
            provider_id=ProviderId.OPENROUTER,
            model="meta-llama/llama-3.1-8b-instruct:free",
            display_name="Llama 3.1 8B (free)",
            cost_tier="free",
        ),
        ModelCatalogEntry(
            id="openrouter/gemma-2-9b-it-free",
            provider_id=ProviderId.OPENROUTER,
            model="google/gemma-2-9b-it:free",
            display_name="Gemma 2 9B (free)",
            cost_tier="free",
        ),
        ModelCatalogEntry(
            id="openrouter/gpt-4.1",
            provider_id=ProviderId.OPENROUTER,
            model="openai/gpt-4.1",
            display_name="GPT-4.1 (via OpenRouter)",
            cost_tier="paid",
        ),
        ModelCatalogEntry(
            id="openrouter/gemini-2.5-pro",
            provider_id=ProviderId.OPENROUTER,
            model="google/gemini-2.5-pro",
            display_name="Gemini 2.5 Pro (via OpenRouter)",
            cost_tier="paid",
        ),
        ModelCatalogEntry(
            id="openrouter/grok-4",
            provider_id=ProviderId.OPENROUTER,
            model="x-ai/grok-4",
            display_name="Grok 4 (via OpenRouter)",
            cost_tier="paid",
        ),
        ModelCatalogEntry(
            id="openrouter/dolphin-mixtral-8x22b",
            provider_id=ProviderId.OPENROUTER,
            model="cognitivecomputations/dolphin-mixtral-8x22b",
            display_name="Dolphin Mixtral 8x22B (uncensored)",
            cost_tier="paid",
            uncensored=True,
        ),
        ModelCatalogEntry(
            id="openrouter/lumimaid-70b",
            provider_id=ProviderId.OPENROUTER,
            model="neversleep/llama-3-lumimaid-70b",
            display_name="Lumimaid 70B (uncensored)",
            cost_tier="paid",
            uncensored=True,
        ),
        ModelCatalogEntry(
            id="openai/gpt-4.1",
            provider_id=ProviderId.OPENAI,
            model="gpt-4.1",
            display_name="GPT-4.1 (direct)",
            cost_tier="paid",
        ),
        ModelCatalogEntry(
            id="ollama/dolphin-mixtral",
            provider_id=ProviderId.OLLAMA,
            model="dolphin-mixtral",
            display_name="Dolphin Mixtral (local, uncensored)",
            cost_tier="free",
            uncensored=True,
        ),
        ModelCatalogEntry(
            id="ollama/dolphin-llama3",
            provider_id=ProviderId.OLLAMA,
            model="dolphin-llama3",
            display_name="Dolphin Llama 3 (local, uncensored)",
            cost_tier="free",
            uncensored=True,
        ),
    ]


class Settings(BaseSettings):
    """Runtime configuration for the AI Companion backend.

    Attributes:
        anthropic_api_key: Anthropic API key. Required — there is no default,
            so construction fails if it is not set.
        claude_model: Claude model ID used by `ClaudeProvider`. Kept as
            config (not hardcoded in the provider) so it can be changed
            without a code change.
        openrouter_api_key: OpenRouter API key. `None` disables every
            catalog entry with `provider_id == ProviderId.OPENROUTER`.
        openai_api_key: OpenAI API key. `None` disables every catalog entry
            with `provider_id == ProviderId.OPENAI`.
        ollama_base_url: Base URL of a local/remote Ollama server's
            OpenAI-compatible API. No API key is required for Ollama.
        default_model_id: `ModelCatalogEntry.id` used when a request omits
            `model_id` and no persona-mode routing rule applies.
        intimate_mode_model_id: `ModelCatalogEntry.id` routed to when
            `PersonaConfig.mode == "intimate"` and the request omits an
            explicit `model_id`.
        model_catalog: The full set of selectable (provider, model) pairs.
        cors_allow_origins: Origins allowed to call this API from a browser.
            Defaults to the local Vite dev server.
    """

    anthropic_api_key: str
    claude_model: str = "claude-opus-5"

    openrouter_api_key: str | None = None
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434/v1"

    default_model_id: str = "claude/claude-opus-5"
    intimate_mode_model_id: str = "openrouter/dolphin-mixtral-8x22b"
    model_catalog: list[ModelCatalogEntry] = Field(default_factory=_default_catalog)

    cors_allow_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def _has_credentials(self, provider_id: ProviderId) -> bool:
        """Whether the given provider has what it needs to be called."""
        if provider_id == ProviderId.CLAUDE:
            return bool(self.anthropic_api_key)
        if provider_id == ProviderId.OPENROUTER:
            return bool(self.openrouter_api_key)
        if provider_id == ProviderId.OPENAI:
            return bool(self.openai_api_key)
        if provider_id == ProviderId.OLLAMA:
            return bool(self.ollama_base_url)
        return False

    def enabled_catalog(self) -> list[ModelCatalogEntry]:
        """Catalog entries that are both `enabled` and actually callable.

        Filters out entries whose provider has no configured credentials, so
        the API/frontend never offer a model that would fail on first use.
        """
        return [
            entry
            for entry in self.model_catalog
            if entry.enabled and self._has_credentials(entry.provider_id)
        ]

    def catalog_entry(self, model_id: str) -> ModelCatalogEntry:
        """Look up an enabled catalog entry by id.

        Args:
            model_id: A `ModelCatalogEntry.id`.

        Returns:
            The matching entry.

        Raises:
            ProviderConfigError: No enabled entry has this id.
        """
        for entry in self.enabled_catalog():
            if entry.id == model_id:
                return entry
        raise ProviderConfigError(f"Unknown or disabled model_id: {model_id!r}")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` instance, constructed once and cached."""
    return Settings()
