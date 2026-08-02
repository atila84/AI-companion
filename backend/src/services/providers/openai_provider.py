"""`CompanionModelProvider` implementation backed directly by the OpenAI API.

Unlike `OpenRouterProvider`, this talks to `api.openai.com` directly rather
than through a proxy — a second example of the `OpenAICompatibleProvider`
pattern for a natively-integrated (non-proxied) backend.
"""

from src.services.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Streams companion replies from the OpenAI API."""
