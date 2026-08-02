"""FastAPI application entrypoint."""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from src.api.routes.chat import router as chat_router
from src.api.routes.models import router as models_router
from src.config import get_settings


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
    except ValidationError:
        sys.stderr.write(
            "\nFATAL: ANTHROPIC_API_KEY is not set.\n"
            "Copy backend/.env.example to backend/.env and set your key, "
            "then restart.\n\n"
        )
        raise

    app = FastAPI(title="AI Companion API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_router)
    app.include_router(models_router)
    return app


app = create_app()
