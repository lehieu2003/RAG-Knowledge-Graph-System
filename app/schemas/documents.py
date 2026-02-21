"""
API schemas for documents
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    id: str
    filename: str
    size_bytes: int
    mime_type: str
    created_at: datetime
    metadata: Dict[str, Any] = {}
    
    # Auto-triggered ingestion job info
    job_id: Optional[str] = None
    task_id: Optional[str] = None
    ingestion_status: Optional[str] = None


class DocumentResponse(BaseModel):
    """Document details"""
    id: str
    filename: str
    size_bytes: int
    mime_type: str
    user_id: str
    tenant_id: str
    created_at: datetime
    metadata: Dict[str, Any] = {}


class DocumentListResponse(BaseModel):
    """List of documents"""
    documents: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    """Chunk details"""
    id: str
    doc_id: str
    text: str
    page_start: int
    page_end: int
    position: int
    created_at: datetime
