"""The `ImageGenerationProvider` interface.

Mirrors `services/providers/base.py::CompanionModelProvider`: no code outside
this module and its concrete implementations may know which image-generation
backend is in use. Unlike chat replies, image generation is a single-shot
result rather than a token stream, so the interface returns one value instead
of yielding an `AsyncIterator`.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class ImageGenerationConfig(BaseModel):
    """Provider-agnostic generation settings for a single image request.

    Attributes:
        model: Backend-specific model identifier.
    """

    model: str


class ImageGenerationProvider(ABC):
    """Abstraction every image-generation backend implements."""

    @abstractmethod
    async def generate_image(self, prompt: str, config: ImageGenerationConfig) -> str:
        """Generate a single image for the given prompt.

        Args:
            prompt: The image description to generate from.
            config: Model parameters for this request.

        Returns:
            An image URL or a `data:image/...;base64,...` URI the frontend
            can load directly in an `<img>` tag.

        Raises:
            ProviderConfigError: The backend is misconfigured.
            ProviderAPIError: The backend call failed.
        """
        raise NotImplementedError
