"""Model catalog API routes."""

from fastapi import APIRouter, Depends

from src.config import ModelCatalogEntry, Settings, get_settings

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
