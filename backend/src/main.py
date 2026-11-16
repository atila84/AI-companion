"""FastAPI application entrypoint."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.api.routes.models import router as models_router
from src.config import get_settings
from src.db import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Release pooled database connections on shutdown.

    Nothing is opened on startup: a well-formed `DATABASE_URL` is validated by
    `Settings` (fail-fast), while actual reachability is a transient condition
    reported by `/health` rather than a reason to refuse to boot.

    Args:
        app: The application being started.

    Yields:
        Control for the lifetime of the application.
    """
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Loads `Settings` at call time (i.e. at module import, before uvicorn
    binds a port) so a missing `ANTHROPIC_API_KEY` fails immediately with a
    clear message rather than surfacing as an obscure error on the first
    chat request.

    Returns:
        The configured `FastAPI` app.
    """
    try:
        settings = get_settings()
    except ValidationError as exc:
        sys.stderr.write(
            f"\nFATAL: invalid backend configuration.\n{exc}\n\n"
            "Check backend/.env against backend/.env.example — a required "
            "setting (ANTHROPIC_API_KEY, DATABASE_URL) is missing or "
            "malformed.\n\n"
        )
        raise

    app = FastAPI(title="AI Companion API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(models_router)
    return app


app = create_app()
