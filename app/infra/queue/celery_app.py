"""
Celery application for async job processing
Production-ready with retries and monitoring
"""
import asyncio
from celery import Celery
from celery.signals import setup_logging, worker_process_init

from app.core.config import get_settings
from app.core.logging import setup_logging as setup_app_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "rag_kg_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.infra.queue.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)


@setup_logging.connect
def setup_celery_logging(**kwargs):
    """Setup logging for Celery workers"""
    setup_app_logging()


@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize database connections when worker process starts"""
    from app.infra.postgres.database import init_db
    from app.infra.neo4j.driver import init_neo4j_sync
    from app.infra.neo4j.repo import Neo4jKnowledgeGraphRepository
    
    # Run Postgres initialization in event loop (it's async)
    asyncio.run(_async_init_postgres())
    
    # Initialize sync Neo4j driver (avoids event loop conflicts in Celery)
    init_neo4j_sync()
    logger.info("neo4j_sync_initialized_for_worker")
    
    # Create Neo4j constraints
    kg_repo = Neo4jKnowledgeGraphRepository()
    kg_repo.create_constraints_sync()
    
    logger.info("celery_worker_initialized")


async def _async_init_postgres():
    """Async initialization of Postgres only"""
    from app.infra.postgres.database import init_db
    
    try:
        await init_db()
        logger.info("celery_worker_databases_initialized")
    except Exception as e:
        logger.exception("celery_worker_init_failed", error=str(e))
        raise
