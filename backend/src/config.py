"""Application configuration.

Settings are loaded from environment variables / a local `.env` file. Construction
deliberately fails fast (a `pydantic.ValidationError`) when `ANTHROPIC_API_KEY` is
unset, rather than allowing the app to start and fail obscurely on the first chat
request — see `src/main.py` for how this is surfaced as a clear startup error.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AI Companion backend.

    Attributes:
        anthropic_api_key: Anthropic API key. Required — there is no default,
            so construction fails if it is not set.
        claude_model: Claude model ID used by `ClaudeProvider`. Kept as
            config (not hardcoded in the provider) so it can be changed
            without a code change.
        cors_allow_origins: Origins allowed to call this API from a browser.
            Defaults to the local Vite dev server.
    """

    anthropic_api_key: str
    claude_model: str = "claude-opus-5"
    cors_allow_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` instance, constructed once and cached."""
    return Settings()
