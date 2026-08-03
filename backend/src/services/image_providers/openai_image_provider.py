"""`ImageGenerationProvider` implementation backed directly by the OpenAI API.

Paid and subject to OpenAI's own content filtering — the counterpart to the
two free/uncensored image providers.
"""

import openai

from src.services.image_providers.base import ImageGenerationConfig, ImageGenerationProvider
from src.services.providers.exceptions import ProviderAPIError


class OpenAIImageProvider(ImageGenerationProvider):
    """Generates images via OpenAI's `images.generate` endpoint."""

    def __init__(self, client: openai.AsyncOpenAI) -> None:
        """Initialize the provider.

        Args:
            client: A configured `AsyncOpenAI` client carrying the API key.
                Client construction happens in `services/image_providers/registry.py`.
        """
        self._client = client

    async def generate_image(self, prompt: str, config: ImageGenerationConfig) -> str:
        """Generate an image via the OpenAI images API.

        Args:
            prompt: The image description to generate from.
            config: `model` is the OpenAI image model (e.g. `"dall-e-3"`).

        Returns:
            The image URL returned by OpenAI.

        Raises:
            ProviderAPIError: The API call failed or returned no image.
        """
        try:
            response = await self._client.images.generate(model=config.model, prompt=prompt, n=1)
        except openai.APIError as exc:
            raise ProviderAPIError(f"OpenAI image request failed: {exc}") from exc

        if not response.data or not response.data[0].url:
            raise ProviderAPIError("OpenAI image response contained no image URL.")
        return response.data[0].url
