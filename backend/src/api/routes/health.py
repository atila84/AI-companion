"""Health check routes."""

from fastapi import APIRouter, Response, status

from src.db import check_connection
from src.models.health import DependencyHealth, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(response: Response) -> HealthResponse:
    """Report whether the service and its dependencies are usable.

    Returns 503 when a dependency is down, so a load balancer or uptime check
    can act on the status code alone without parsing the body.

    Args:
        response: Injected so the status code can be set per result.

    Returns:
        The service status and per-dependency detail.
    """
    reachable, error = await check_connection()
    database = DependencyHealth(ok=reachable, detail=error)

    if not reachable:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(status="ok" if reachable else "degraded", database=database)
