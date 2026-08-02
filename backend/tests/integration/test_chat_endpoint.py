"""Integration tests for `POST /api/chat/stream`.

The provider dependency is overridden with an in-process fake — no real
Anthropic API call is made.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from src.api.deps import get_provider
from src.models.chat import ChatMessage, ChatRole
from src.personas.base import PersonaConfig
from src.services.providers.base import CompanionModelProvider, ProviderConfig
from src.services.providers.exceptions import ProviderAPIError


class _FakeProvider(CompanionModelProvider):
    def __init__(self, tokens: list[str] | None = None, error: Exception | None = None) -> None:
        self._tokens = tokens or []
        self._error = error

    async def stream_reply(
        self,
        messages: list[ChatMessage],
        persona: PersonaConfig,
        config: ProviderConfig,
    ) -> AsyncIterator[str]:
        if self._error is not None:
            raise self._error
        for token in self._tokens:
            yield token


@pytest.fixture
def app_module():
    """Import the app fresh per test with ANTHROPIC_API_KEY guaranteed set."""
    import os

    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
    from src.main import app

    return app


async def _post_chat(app, provider: CompanionModelProvider) -> httpx.Response:
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/chat/stream",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
    finally:
        app.dependency_overrides.pop(get_provider, None)


async def test_stream_chat_returns_token_and_done_chunks(app_module) -> None:
    response = await _post_chat(app_module, _FakeProvider(tokens=["Hello", " ", "world"]))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert 'data: {"type":"token","content":"Hello"}' in body
    assert 'data: {"type":"token","content":" "}' in body
    assert 'data: {"type":"token","content":"world"}' in body
    assert body.strip().endswith('data: {"type":"done","content":null}')


async def test_stream_chat_returns_error_chunk_on_provider_failure(app_module) -> None:
    response = await _post_chat(app_module, _FakeProvider(error=ProviderAPIError("upstream down")))

    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert "upstream down" in response.text


async def test_stream_chat_rejects_malformed_body(app_module) -> None:
    app_module.dependency_overrides[get_provider] = lambda: _FakeProvider()
    try:
        transport = ASGITransport(app=app_module)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/chat/stream", json={})
    finally:
        app_module.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 422
