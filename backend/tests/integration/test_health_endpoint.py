"""Integration tests for `GET /health` (S1.1.1).

The reachable case runs against the real local Postgres and is skipped when
none is available, so the suite still passes on a machine without a database.
The unreachable case needs no database at all — it points the engine at a dead
port, which is the condition we actually care about reporting.
"""

import os

import httpx
import pytest
from httpx import ASGITransport

from src.config import Settings, get_settings
from src.db import build_engine, check_connection

LOCAL_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://localhost/ai_companion")
DEAD_URL = "postgresql+asyncpg://localhost:1/nope"


def _settings(url: str) -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        anthropic_api_key="sk-ant-test",
        database_url=url,
    )


@pytest.fixture
def app_module():
    """Import the app with the required settings present."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
    os.environ.setdefault("DATABASE_URL", LOCAL_URL)
    from src.main import app

    return app


async def _database_available() -> bool:
    engine = build_engine(_settings(LOCAL_URL))
    try:
        reachable, _ = await check_connection(engine)
        return reachable
    finally:
        await engine.dispose()


async def _get_health(app, url: str) -> httpx.Response:
    """Call /health with the app's settings pointed at `url`."""
    app.dependency_overrides[get_settings] = lambda: _settings(url)
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")
    finally:
        app.dependency_overrides.pop(get_settings, None)


async def test_health_reports_ok_when_database_is_reachable(app_module) -> None:
    if not await _database_available():
        pytest.skip(f"no Postgres at {LOCAL_URL}")

    response = await _get_health(app_module, LOCAL_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True
    assert body["database"]["detail"] is None


async def test_check_connection_reports_why_it_failed() -> None:
    """A failing health check must say *why*, or it just sends you to the logs."""
    engine = build_engine(_settings(DEAD_URL))
    try:
        reachable, detail = await check_connection(engine)
    finally:
        await engine.dispose()

    assert reachable is False
    assert detail, "an unreachable database must report a reason"


async def test_check_connection_succeeds_against_the_real_database() -> None:
    if not await _database_available():
        pytest.skip(f"no Postgres at {LOCAL_URL}")

    engine = build_engine(_settings(LOCAL_URL))
    try:
        assert await check_connection(engine) == (True, None)
    finally:
        await engine.dispose()
