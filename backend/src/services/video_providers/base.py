"""The `VideoGenerationProvider` interface.

Mirrors `services/image_providers/base.py::ImageGenerationProvider`: no code
outside this module and its concrete implementations may know which
video-generation backend is in use. Video generation is also a single-shot
result rather than a token stream, so the interface returns one value
instead of yielding an `AsyncIterator`.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class VideoGenerationConfig(BaseModel):
    """Provider-agnostic generation settings for a single video request.

    Attributes:
        model: Backend-specific model identifier.
    """

    model: str


class VideoGenerationProvider(ABC):
    """Abstraction every video-generation backend implements."""

    @abstractmethod
    async def generate_video(self, prompt: str, config: VideoGenerationConfig) -> str:
        """Generate a single video for the given prompt.

        Args:
            prompt: The video description to generate from.
            config: Model parameters for this request.

        Returns:
            A video URL or a `data:video/...;base64,...` URI the frontend
            can load directly in a `<video>` tag.

        Raises:
            ProviderConfigError: The backend is misconfigured.
            ProviderAPIError: The backend call failed.
        """
        raise NotImplementedError
