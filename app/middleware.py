import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from .metrics import increment, record_duration

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()

        response = await call_next(request)

        duration = round(time.time() - start, 4)
        
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": duration,
            }
        )

        increment("http_requests_total")
        if response.status_code >= 400:
            increment("http_errors_total")
        record_duration("http_request", duration)

        return response