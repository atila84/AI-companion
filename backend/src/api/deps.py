"""FastAPI dependency wiring.

Centralizing construction here (rather than instantiating services inline in
route handlers) is also what makes `test_chat_endpoint.py` able to swap in a
fake `ProviderResolver` via `app.dependency_overrides[get_provider_resolver]`
without touching the route or service code.
"""

from fastapi import Depends

from src.config import Settings, get_settings
from src.services.chat_service import ChatService
from src.services.image_router import ImageProviderResolver
from src.services.provider_router import ProviderResolver
from src.services.safety.image_content_guard import ImageContentGuard
from src.services.safety.uncensored_guard import UncensoredSafetyGuard
from src.services.safety.video_content_guard import VideoContentGuard
from src.services.video_router import VideoProviderResolver


def get_provider_resolver(settings: Settings = Depends(get_settings)) -> ProviderResolver:
    """Return a `ProviderResolver` wired to the active settings/catalog."""
    return ProviderResolver(settings)


def get_safety_guard() -> UncensoredSafetyGuard:
    """Return the `UncensoredSafetyGuard` applied to uncensored providers."""
    return UncensoredSafetyGuard()


def get_image_resolver(settings: Settings = Depends(get_settings)) -> ImageProviderResolver:
    """Return an `ImageProviderResolver` wired to the active settings/catalog."""
    return ImageProviderResolver(settings)


def get_image_content_guard() -> ImageContentGuard:
    """Return the `ImageContentGuard` applied to every image prompt."""
    return ImageContentGuard()


def get_video_resolver(settings: Settings = Depends(get_settings)) -> VideoProviderResolver:
    """Return a `VideoProviderResolver` wired to the active settings/catalog."""
    return VideoProviderResolver(settings)


def get_video_content_guard() -> VideoContentGuard:
    """Return the `VideoContentGuard` applied to every video prompt."""
    return VideoContentGuard()


def get_chat_service(
    resolver: ProviderResolver = Depends(get_provider_resolver),
    safety_guard: UncensoredSafetyGuard = Depends(get_safety_guard),
    image_resolver: ImageProviderResolver = Depends(get_image_resolver),
    image_content_guard: ImageContentGuard = Depends(get_image_content_guard),
    video_resolver: VideoProviderResolver = Depends(get_video_resolver),
    video_content_guard: VideoContentGuard = Depends(get_video_content_guard),
) -> ChatService:
    """Return a `ChatService` wired to provider resolution and the safety guards."""
    return ChatService(
        resolver, safety_guard, image_resolver, image_content_guard, video_resolver, video_content_guard
    )
