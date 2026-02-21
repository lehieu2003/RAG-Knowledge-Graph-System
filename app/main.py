"""
Main FastAPI Application
Production-ready RAG Knowledge Graph System
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import setup_middleware
from app.infra.postgres.database import init_db, close_db
from app.infra.neo4j.driver import init_neo4j, close_neo4j
from app.infra.neo4j.repo import Neo4jKnowledgeGraphRepository

# API routers
from app.api.routers import (
    documents,
    ingestion,
    kg,
    chat,
    health
)

settings = get_settings()

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    # Startup
    logger.info("application_starting", app=settings.app_name, version=settings.app_version)
    
    try:
        # Initialize databases
        await init_db()
        await init_neo4j()
        
        # Initialize Neo4j schema
        kg_repo = Neo4jKnowledgeGraphRepository()
        await kg_repo.create_constraints()
        
        logger.info("application_started", environment=settings.environment)
        
    except Exception as e:
        logger.exception("startup_failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    
    try:
        await close_db()
        await close_neo4j()
        logger.info("application_stopped")
    except Exception as e:
        logger.exception("shutdown_error", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready RAG Knowledge Graph System with Hybrid Extraction + GraphRAG/TextRAG",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Setup middleware
setup_middleware(app)

# Register routers
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ingestion.router)
app.include_router(kg.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.is_development else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
