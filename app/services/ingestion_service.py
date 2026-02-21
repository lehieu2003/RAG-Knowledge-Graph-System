"""
Ingestion Service - Job orchestration
Manages ingestion pipeline execution
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from app.domain.ports import JobRepository
from app.domain.models import IngestionJob, JobStatus, JobStep
from app.core.logging import get_logger
from app.core.exceptions import JobNotFoundError

logger = get_logger(__name__)


class IngestionService:
    """Ingestion job management"""
    
    def __init__(self, job_repo: JobRepository):
        self.job_repo = job_repo
    
    async def create_job(
        self,
        doc_id: str,
        user_id: str,
        tenant_id: str
    ) -> IngestionJob:
        """Create new ingestion job"""
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        
        job = IngestionJob(
            id=job_id,
            doc_id=doc_id,
            status=JobStatus.PENDING,
            current_step=None,
            progress={},
            user_id=user_id,
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        await self.job_repo.create(job)
        logger.info("ingestion_job_created", job_id=job_id, doc_id=doc_id)
        
        return job
    
    async def get_job(self, job_id: str, tenant_id: str) -> IngestionJob:
        """Get job by ID"""
        job = await self.job_repo.get_by_id(job_id, tenant_id)
        if not job:
            raise JobNotFoundError(job_id)
        return job
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        current_step: Optional[JobStep] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update job status"""
        result = await self.job_repo.update_status(
            job_id, status, current_step, error_message
        )
        logger.info("job_status_updated", job_id=job_id, status=status.value)
        return result
    
    async def update_job_progress(
        self,
        job_id: str,
        step: JobStep,
        step_status: str,
        stats: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update progress for specific step"""
        job = await self.job_repo.get_by_id(job_id, "")  # TODO: proper tenant handling
        if not job:
            return False
        
        progress = job.progress.copy()
        progress[step.value] = {
            "status": step_status,
            "stats": stats or {},
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        result = await self.job_repo.update_progress(job_id, progress)
        logger.info("job_progress_updated", job_id=job_id, step=step.value, status=step_status)
        return result
    
    async def list_jobs(
        self,
        tenant_id: str,
        status: Optional[JobStatus] = None
    ):
        """List jobs for tenant"""
        return await self.job_repo.list_by_tenant(tenant_id, status)
    
    def submit_to_queue(self, job_id: str, tenant_id: str):
        """Submit job to Celery queue"""
        from app.infra.queue.tasks import run_ingestion_pipeline
        
        task = run_ingestion_pipeline.delay(job_id, tenant_id)
        logger.info("job_submitted_to_queue", job_id=job_id, task_id=task.id)
        return task.id
