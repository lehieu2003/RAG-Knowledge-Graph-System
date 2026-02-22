"""
Celery tasks for async ingestion pipeline
Idempotent, retryable, and observable
"""
from typing import Dict, Any
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.infra.queue.celery_app import celery_app
from app.core.logging import get_logger, set_correlation_id

logger = get_logger(__name__)


class IngestionTask(Task):
    """Base task with error handling and logging"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 5}  # Wait 5 seconds before retry
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=IngestionTask,
    name="ingestion.run_pipeline"
)
def run_ingestion_pipeline(self, job_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Run full ingestion pipeline for a job
    This is the main entry point for async processing
    
    Args:
        job_id: Ingestion job ID
        tenant_id: Tenant ID for isolation
    
    Returns:
        Dict with status and results
    """
    # Set correlation ID for tracing
    set_correlation_id(job_id)
    
    logger.info("ingestion_task_started", job_id=job_id, tenant_id=tenant_id)
    
    try:
        # Import here to avoid circular dependencies
        from app.pipelines.ingest_pipeline import run_full_pipeline
        
        # Run pipeline (blocks until complete or error)
        result = run_full_pipeline(job_id, tenant_id)
        
        logger.info("ingestion_task_completed", job_id=job_id, result=result)
        return result
        
    except SoftTimeLimitExceeded:
        logger.error("ingestion_task_timeout", job_id=job_id)
        return {"status": "timeout", "job_id": job_id}
    
    except Exception as e:
        logger.exception("ingestion_task_failed", job_id=job_id, error=str(e))
        raise


@celery_app.task(name="health.check")
def health_check() -> Dict[str, str]:
    """Health check task for monitoring"""
    return {"status": "healthy", "worker": "celery"}
