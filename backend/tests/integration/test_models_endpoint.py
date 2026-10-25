"""Integration tests for the `GET /api/models*` catalog routes.

`Settings` is overridden per test (rather than relying on whatever a
developer's local `backend/.env` happens to contain) so which catalog
entries come back as "enabled" is deterministic.
"""

import os

import httpx
import pytest
from httpx import ASGITransport

from src.config import Settings, get_settings


@pytest.fixture
def app_module():
    """Import the app fresh per test with ANTHROPIC_API_KEY guaranteed set."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
    from src.main import app

    return app


async def _get(app, path: str, settings: Settings) -> httpx.Response:
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)
    finally:
        app.dependency_overrides.pop(get_settings, None)


def _settings(**overrides: str | None) -> Settings:
    return Settings(_env_file=None, anthropic_api_key="sk-ant-test-key", **overrides)  # type: ignore[call-arg]


async def test_list_models_returns_enabled_text_catalog(app_module) -> None:
    response = await _get(app_module, "/api/models", _settings())

    assert response.status_code == 200
    ids = [entry["id"] for entry in response.json()]
    assert "claude/claude-opus-5" in ids
    assert "openrouter/gpt-4.1" not in ids  # no OPENROUTER_API_KEY configured


async def test_list_image_models_returns_enabled_image_catalog(app_module) -> None:
    response = await _get(app_module, "/api/models/images", _settings())

    assert response.status_code == 200
    ids = [entry["id"] for entry in response.json()]
    # Pollinations needs no credentials, so it's always enabled. Two entries
    # exist so there is a real choice to make without any setup.
    assert "pollinations/flux" in ids
    assert "pollinations/turbo" in ids
    assert "openai/dall-e-3" not in ids  # no OPENAI_API_KEY configured


async def test_list_image_models_includes_openai_when_configured(app_module) -> None:
    response = await _get(app_module, "/api/models/images", _settings(openai_api_key="sk-test"))

    ids = [entry["id"] for entry in response.json()]
    assert "openai/dall-e-3" in ids


async def test_list_video_models_excludes_unconfigured_providers(app_module) -> None:
    response = await _get(app_module, "/api/models/videos", _settings())

    assert response.status_code == 200
    assert response.json() == []


async def test_list_video_models_includes_comfyui_when_configured(app_module) -> None:
    response = await _get(
        app_module, "/api/models/videos", _settings(comfyui_base_url="http://localhost:8188")
    )

    ids = [entry["id"] for entry in response.json()]
    assert "comfyui/wan2.2" in ids
    assert "openai/sora-2" not in ids
