"""`ImageGenerationProvider` implementation backed by Pollinations.ai.

Free, hosted, and requires no API key or account. The image is served
directly from `image.pollinations.ai`, so this provider returns that URL
rather than fetching and re-serving the bytes itself — the frontend `<img>`
loads it straight from Pollinations.
"""

from urllib.parse import quote

from src.services.image_providers.base import ImageGenerationConfig, ImageGenerationProvider

POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"


class PollinationsProvider(ImageGenerationProvider):
    """Builds a Pollinations.ai image URL for the given prompt."""

    async def generate_image(self, prompt: str, config: ImageGenerationConfig) -> str:
        """Return the Pollinations.ai URL that renders `prompt`.

        Args:
            prompt: The image description to generate from.
            config: `model` selects the Pollinations model (e.g. `"flux"`).

        Returns:
            A fully-formed Pollinations.ai image URL.
        """
        encoded_prompt = quote(prompt)
        return f"{POLLINATIONS_BASE_URL}/{encoded_prompt}?model={config.model}&nologo=true"
