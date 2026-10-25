"""`VideoGenerationProvider` implementation backed by a local ComfyUI-
compatible server running an open-weight video model (e.g. Wan 2.2,
HunyuanVideo).

Free and fully uncensored since it's self-hosted — same "local, no API key,
base_url-configured" shape as `services/image_providers/automatic1111_provider.py`.
ComfyUI's native API is a graph-submission workflow rather than a single
txt2vid endpoint; `/prompt` here assumes a server fronted with a simple
txt2vid-compatible route (e.g. a ComfyUI custom node or a thin wrapper) that
accepts `{"prompt": ...}` and returns the finished video inline, matching the
one-call shape every other provider in this codebase uses.
"""

import httpx

from src.services.providers.exceptions import ProviderAPIError
from src.services.video_providers.base import VideoGenerationConfig, VideoGenerationProvider


class ComfyUIVideoProvider(VideoGenerationProvider):
    """Calls a local ComfyUI-compatible txt2vid endpoint."""

    def __init__(self, base_url: str) -> None:
        """Initialize the provider.

        Args:
            base_url: Base URL of the local ComfyUI-compatible server, e.g.
                `"http://localhost:8188"`.
        """
        self._base_url = base_url.rstrip("/")

    async def generate_video(self, prompt: str, config: VideoGenerationConfig) -> str:
        """Generate a video via a local ComfyUI-compatible txt2vid endpoint.

        Args:
            prompt: The video description to generate from.
            config: `model` is informational only here — the server generates
                with whichever checkpoint it currently has loaded.

        Returns:
            A `data:video/mp4;base64,...` URI of the generated video.

        Raises:
            ProviderAPIError: The txt2vid call failed or returned no video.
        """
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"{self._base_url}/txt2vid",
                    json={"prompt": prompt},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ProviderAPIError(f"ComfyUI video request failed: {exc}") from exc

        videos = payload.get("videos") or []
        if not videos:
            raise ProviderAPIError("ComfyUI response contained no videos.")
        return f"data:video/mp4;base64,{videos[0]}"
