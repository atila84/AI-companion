"""`VideoGenerationProvider` implementation backed directly by the OpenAI
Sora video API.

Paid and subject to OpenAI's own content filtering — the counterpart to the
free/uncensored `ComfyUIVideoProvider`. Unlike `images.generate`, OpenAI's
video API is job-based: `create_and_poll` submits the job and blocks until it
finishes, then `download_content` fetches the rendered bytes.
"""

import base64

import openai

from src.services.providers.exceptions import ProviderAPIError
from src.services.video_providers.base import VideoGenerationConfig, VideoGenerationProvider


class OpenAIVideoProvider(VideoGenerationProvider):
    """Generates videos via OpenAI's `videos.create_and_poll` endpoint."""

    def __init__(self, client: openai.AsyncOpenAI) -> None:
        """Initialize the provider.

        Args:
            client: A configured `AsyncOpenAI` client carrying the API key.
                Client construction happens in `services/video_providers/registry.py`.
        """
        self._client = client

    async def generate_video(self, prompt: str, config: VideoGenerationConfig) -> str:
        """Generate a video via the OpenAI videos API.

        Args:
            prompt: The video description to generate from.
            config: `model` is the OpenAI video model (e.g. `"sora-2"`).

        Returns:
            A `data:video/mp4;base64,...` URI of the generated video.

        Raises:
            ProviderAPIError: The job failed, or the API call errored.
        """
        try:
            video = await self._client.videos.create_and_poll(model=config.model, prompt=prompt)
            if video.status != "completed":
                raise ProviderAPIError(f"OpenAI video job did not complete: status={video.status}")
            content = await self._client.videos.download_content(video.id)
        except openai.APIError as exc:
            raise ProviderAPIError(f"OpenAI video request failed: {exc}") from exc

        return f"data:video/mp4;base64,{base64.b64encode(content.content).decode()}"
