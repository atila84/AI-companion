"""Model catalog API routes."""

from fastapi import APIRouter, Depends

from src.config import ImageCatalogEntry, ModelCatalogEntry, Settings, VideoCatalogEntry, get_settings

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_models(settings: Settings = Depends(get_settings)) -> list[ModelCatalogEntry]:
    """List the models currently selectable via `ChatRequest.model_id`.

    Only returns catalog entries whose provider has configured credentials —
    the frontend never offers a model that would fail on first use.

    Args:
        settings: Injected application settings.

    Returns:
        The enabled model catalog.
    """
    return settings.enabled_catalog()


@router.get("/images")
async def list_image_models(settings: Settings = Depends(get_settings)) -> list[ImageCatalogEntry]:
    """List the models available for auto-detected image generation.

    Informational only — there is no per-request way to choose one of these
    yet (see `services/image_router.py::ImageProviderResolver`, which always
    resolves to `Settings.default_image_model_id`). Exposed so the frontend
    can show the user what's available.

    Args:
        settings: Injected application settings.

    Returns:
        The enabled image-generation catalog.
    """
    return settings.enabled_image_catalog()


@router.get("/videos")
async def list_video_models(settings: Settings = Depends(get_settings)) -> list[VideoCatalogEntry]:
    """List the models available for auto-detected video generation.

    Informational only — same caveat as `list_image_models`: there is no
    per-request way to choose one of these yet.

    Args:
        settings: Injected application settings.

    Returns:
        The enabled video-generation catalog.
    """
    return settings.enabled_video_catalog()
