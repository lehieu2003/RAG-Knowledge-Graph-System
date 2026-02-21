"""
Structured logging with correlation IDs
Production-ready observability
"""
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional
import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings

# Context var for correlation ID (request tracing)
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log context"""
    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context"""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def setup_logging() -> None:
    """Configure structured logging"""
    settings = get_settings()
    
    # Shared processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_correlation_id,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Development: pretty console, Production: JSON
    if settings.is_development:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context"""
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_ctx.get()
