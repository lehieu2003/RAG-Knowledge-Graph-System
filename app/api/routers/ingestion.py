"""
Ingestion API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List

from app.api.deps import get_ingestion_service, get_current_user_id, get_current_tenant_id
from app.services.ingestion_service import IngestionService
from app.schemas.ingestion import (
    IngestionJobCreateRequest,
    IngestionJobResponse,
    IngestionJobSubmitResponse,
    IngestionJobListResponse
)
from app.domain.models import JobStatus
from app.core.logging import get_logger
from app.core.exceptions import JobNotFoundError

logger = get_logger(__name__)
router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/jobs", response_model=IngestionJobSubmitResponse)
async def create_and_submit_job(
    request: IngestionJobCreateRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Create and submit ingestion job"""
    try:
        # Create job
        job = await ingestion_service.create_job(
            doc_id=request.doc_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Submit to queue
        task_id = ingestion_service.submit_to_queue(job.id, tenant_id)
        
        return IngestionJobSubmitResponse(
            job_id=job.id,
            task_id=task_id,
            status="submitted",
            message="Ingestion job submitted to queue"
        )
    
    except Exception as e:
        logger.exception("job_submission_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Job submission failed")


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job(
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Get job status"""
    try:
        job = await ingestion_service.get_job(job_id, tenant_id)
        
        return IngestionJobResponse(
            id=job.id,
            doc_id=job.doc_id,
            status=job.status.value,
            current_step=job.current_step.value if job.current_step else None,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
    
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/jobs", response_model=List[IngestionJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """List ingestion jobs"""
    job_status = JobStatus(status) if status else None
    jobs = await ingestion_service.list_jobs(tenant_id, job_status)
    
    return [
        IngestionJobResponse(
            id=job.id,
            doc_id=job.doc_id,
            status=job.status.value,
            current_step=job.current_step.value if job.current_step else None,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        for job in jobs
    ]
