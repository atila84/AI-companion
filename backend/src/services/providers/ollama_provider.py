"""`CompanionModelProvider` implementation backed by a local/remote Ollama server.

Ollama exposes an OpenAI-compatible `/v1` API, so this reuses
`OpenAICompatibleProvider`. Self-hosted open-weight models run this way are
free to call and require no API key — see `config.py::Settings.ollama_base_url`.
"""

from src.services.providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Streams companion replies from a self-hosted Ollama model."""
