"""
Neo4j driver management
"""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, GraphDatabase, Driver, Session

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Global driver instances
_driver: AsyncDriver | None = None
_sync_driver: Driver | None = None


async def init_neo4j() -> AsyncDriver:
    """Initialize Neo4j driver"""
    global _driver
    
    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_lifetime=3600,
        max_connection_pool_size=50,
        connection_acquisition_timeout=60,
    )
    
    # Verify connectivity
    await _driver.verify_connectivity()
    logger.info("neo4j_connected", uri=settings.neo4j_uri)
    
    return _driver


async def close_neo4j():
    """Close Neo4j driver"""
    global _driver
    if _driver:
        await _driver.close()
        logger.info("neo4j_closed")
        _driver = None


def get_driver() -> AsyncDriver:
    """Get Neo4j driver"""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_neo4j() first.")
    return _driver


def init_neo4j_sync() -> Driver:
    """Initialize sync Neo4j driver for Celery tasks"""
    global _sync_driver
    
    if _sync_driver is None:
        _sync_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
        
        # Verify connectivity
        _sync_driver.verify_connectivity()
        logger.info("neo4j_sync_connected", uri=settings.neo4j_uri)
    
    return _sync_driver


def close_neo4j_sync():
    """Close sync Neo4j driver"""
    global _sync_driver
    if _sync_driver:
        _sync_driver.close()
        logger.info("neo4j_sync_closed")
        _sync_driver = None


def get_sync_driver() -> Driver:
    """Get sync Neo4j driver (creates if not exists)"""
    return init_neo4j_sync()


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    """Get Neo4j session (context manager)"""
    driver = get_driver()
    async with driver.session() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_neo4j_session_sync() -> Generator[Session, None, None]:
    """Get sync Neo4j session for Celery tasks"""
    driver = get_sync_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()
