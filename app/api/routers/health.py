"""
Health check endpoints
"""
from fastapi import APIRouter
from datetime import datetime

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check (can add DB/Neo4j/Redis checks)"""
    # TODO: Add actual dependency checks
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ok",
            "neo4j": "ok",
            "redis": "ok"
        }
    }
