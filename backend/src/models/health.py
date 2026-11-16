"""API models for the health endpoint."""

from typing import Literal

from pydantic import BaseModel, Field


class DependencyHealth(BaseModel):
    """Reachability of one external dependency.

    Attributes:
        ok: Whether the dependency responded.
        detail: Error message when `ok` is False, otherwise `None`. Surfaced so
            a failing check says *why* without requiring a server-log dive.
    """

    ok: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    """Response body for `GET /health`.

    Attributes:
        status: `"ok"` when every dependency is reachable, else `"degraded"`.
        database: Postgres reachability.
    """

    status: Literal["ok", "degraded"] = Field(description="Overall service status")
    database: DependencyHealth
