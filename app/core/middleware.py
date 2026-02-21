"""
Middleware for request tracking, error handling, and observability
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.logging import get_logger, set_correlation_id, get_correlation_id
from app.core.exceptions import AppException
from app.core.config import get_settings

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to every request for distributed tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling with proper status codes"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except AppException as exc:
            logger.error(
                "application_error",
                error_code=exc.code,
                message=exc.message,
                details=exc.details,
                status_code=exc.status_code,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "correlation_id": get_correlation_id(),
                },
            )
        except Exception as exc:
            logger.exception("unexpected_error", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": get_correlation_id(),
                },
            )


def setup_middleware(app):
    """Configure all middleware"""
    settings = get_settings()
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware (order matters!)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
