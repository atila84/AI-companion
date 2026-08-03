"""`ImageGenerationProvider` implementation backed by a local Automatic1111/
ComfyUI-compatible Stable Diffusion WebUI server.

Free and fully uncensored since it's self-hosted — same "local, no API key,
base_url-configured" shape as `services/providers/ollama_provider.py`.
"""

import httpx

from src.services.image_providers.base import ImageGenerationConfig, ImageGenerationProvider
from src.services.providers.exceptions import ProviderAPIError


class Automatic1111Provider(ImageGenerationProvider):
    """Calls a local Automatic1111 `/sdapi/v1/txt2img` endpoint."""

    def __init__(self, base_url: str) -> None:
        """Initialize the provider.

        Args:
            base_url: Base URL of the local Automatic1111 WebUI server, e.g.
                `"http://localhost:7860"`.
        """
        self._base_url = base_url.rstrip("/")

    async def generate_image(self, prompt: str, config: ImageGenerationConfig) -> str:
        """Generate an image via Automatic1111's txt2img endpoint.

        Args:
            prompt: The image description to generate from.
            config: `model` is informational only here — the WebUI generates
                with whichever checkpoint it currently has loaded.

        Returns:
            A `data:image/png;base64,...` URI of the generated image.

        Raises:
            ProviderAPIError: The txt2img call failed or returned no image.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self._base_url}/sdapi/v1/txt2img",
                    json={"prompt": prompt},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ProviderAPIError(f"Automatic1111 request failed: {exc}") from exc

        images = payload.get("images") or []
        if not images:
            raise ProviderAPIError("Automatic1111 response contained no images.")
        return f"data:image/png;base64,{images[0]}"
