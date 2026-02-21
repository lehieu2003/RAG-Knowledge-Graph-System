"""
API schemas for ingestion
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class IngestionJobCreateRequest(BaseModel):
    """Request to create ingestion job"""
    doc_id: str = Field(..., description="Document ID to ingest")


class IngestionJobResponse(BaseModel):
    """Ingestion job details"""
    id: str
    doc_id: str
    status: str
    current_step: Optional[str] = None
    progress: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class IngestionJobSubmitResponse(BaseModel):
    """Response for job submission"""
    job_id: str
    task_id: str
    status: str
    message: str


class IngestionJobListResponse(BaseModel):
    """List of ingestion jobs"""
    jobs: list[IngestionJobResponse]
    total: int
