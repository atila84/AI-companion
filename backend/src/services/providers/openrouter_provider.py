"""`CompanionModelProvider` implementation backed by OpenRouter.

OpenRouter proxies many upstream models (free, paid, and uncensored/RP-tuned
community models) behind one OpenAI-compatible API and one API key — see
`config.py::_default_catalog` for the specific models exposed through it.
"""

from src.services.providers.openai_compatible import OpenAICompatibleProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(OpenAICompatibleProvider):
    """Streams companion replies from any model OpenRouter proxies."""
