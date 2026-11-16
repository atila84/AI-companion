"""Tests for `DATABASE_URL` validation and engine construction (S1.1.1).

The acceptance criterion is that the backend refuses to start with a clear
error when `DATABASE_URL` is unset or wrong, so most of these assert on the
*message*, not just the failure — an unactionable error is barely better than
a crash.
"""

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.db import build_engine

VALID_URL = "postgresql+asyncpg://localhost/ai_companion"


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {"anthropic_api_key": "sk-ant-test", "database_url": VALID_URL}
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_valid_async_url_is_accepted() -> None:
    assert _settings().database_url == VALID_URL


def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """The headline acceptance criterion: no DATABASE_URL, no startup.

    `_env_file=None` only disables the .env file — pydantic-settings still reads
    the real environment, so the variable has to be cleared explicitly or a
    DATABASE_URL exported for the test run would mask this.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, anthropic_api_key="sk-ant-test")  # type: ignore[call-arg]

    assert "database_url" in str(exc.value).lower()


def test_sync_driver_url_is_rejected_with_the_fix_in_the_message() -> None:
    """`postgresql://` is what every tool prints, so the error must say what to change."""
    with pytest.raises(ValidationError) as exc:
        _settings(database_url="postgresql://localhost/ai_companion")

    message = str(exc.value)
    assert "postgresql+asyncpg://" in message, "error should name the required scheme"


@pytest.mark.parametrize(
    "url",
    ["", "   ", "mysql://localhost/db", "not-a-url", "sqlite+aiosqlite:///:memory:"],
)
def test_non_postgres_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        _settings(database_url=url)


def test_postgres_scheme_variant_is_rejected() -> None:
    """`postgres://` (no 'ql') is the other common spelling and is equally unusable."""
    with pytest.raises(ValidationError) as exc:
        _settings(database_url="postgres://localhost/db")

    assert "postgresql+asyncpg://" in str(exc.value)


def test_pool_settings_have_defaults() -> None:
    settings = _settings()

    assert settings.database_pool_size > 0
    assert settings.database_max_overflow >= 0
    assert settings.database_pool_timeout_seconds > 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_pool_size", 0),
        ("database_pool_size", -1),
        ("database_max_overflow", -1),
        ("database_pool_timeout_seconds", 0),
    ],
)
def test_nonsensical_pool_settings_are_rejected(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: value})


def test_build_engine_accepts_settings_directly() -> None:
    """Regression: `get_engine` was `lru_cache`d with a `Settings` parameter, and
    `Settings` is a Pydantic model and therefore unhashable — passing one raised
    `TypeError: unhashable type`. The cached accessor now takes no arguments."""
    engine = build_engine(_settings())

    assert engine.url.database == "ai_companion"
    assert engine.pool.size() == _settings().database_pool_size


def test_engine_applies_configured_pool_size() -> None:
    engine = build_engine(_settings(database_pool_size=7))

    assert engine.pool.size() == 7
