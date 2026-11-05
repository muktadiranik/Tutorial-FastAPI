from collections.abc import Awaitable, Callable
import logging
from time import perf_counter

from fastapi import Request, Response


logger = logging.getLogger(__name__)


def request_route(request: Request) -> str:
    # Templates avoid logging sensitive path values; unknown URLs are omitted.
    route = request.scope.get("route")
    return getattr(route, "path", "<unmatched>")


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed method=%s route=%s status=500 duration_ms=%.2f",
            request.method, request_route(request),
            (perf_counter() - started_at) * 1000,
        )
        raise

    level = logging.INFO
    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400:
        level = logging.WARNING
    logger.log(
        level, "Request completed method=%s route=%s status=%s duration_ms=%.2f",
        request.method, request_route(request), response.status_code,
        (perf_counter() - started_at) * 1000,
    )
    return response
