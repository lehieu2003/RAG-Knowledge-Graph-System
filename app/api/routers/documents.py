"""
Document API endpoints
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_document_service, get_ingestion_service, get_current_user_id, get_current_tenant_id, get_db
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.schemas.documents import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    ChunkResponse
)
from app.core.logging import get_logger
from app.core.exceptions import DocumentNotFoundError, UploadError

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
    ingestion_service: IngestionService = Depends(get_ingestion_service),    db: AsyncSession = Depends(get_db),  # Direct session access for commit    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Upload a PDF document and auto-trigger knowledge extraction pipeline"""
    try:
        # Read file content
        file_bytes = await file.read()
        
        # Upload document
        document = await doc_service.upload_document(
            filename=file.filename,
            file_bytes=file_bytes,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        logger.info("document_uploaded", doc_id=document.id, filename=document.filename)
        
        # Auto-trigger ingestion pipeline
        try:
            # Create ingestion job
            job = await ingestion_service.create_job(
                doc_id=document.id,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            # IMPORTANT: Commit DB before submitting to queue
            # This ensures Celery worker can find the job record
            await db.commit()
            logger.info("job_committed_to_db", job_id=job.id)
            
            # Submit to queue (Celery)
            task_id = ingestion_service.submit_to_queue(job.id, tenant_id)
            
            logger.info(
                "ingestion_auto_triggered", 
                doc_id=document.id, 
                job_id=job.id, 
                task_id=task_id
            )
            
            return DocumentUploadResponse(
                id=document.id,
                filename=document.filename,
                size_bytes=document.size_bytes,
                mime_type=document.mime_type,
                created_at=document.created_at,
                metadata=document.metadata,
                job_id=job.id,
                task_id=task_id,
                ingestion_status="processing"
            )
            
        except Exception as ingestion_error:
            # Log error but still return document info
            logger.error(
                "ingestion_trigger_failed", 
                doc_id=document.id, 
                error=str(ingestion_error)
            )
            
            # Document uploaded successfully, but ingestion failed to start
            return DocumentUploadResponse(
                id=document.id,
                filename=document.filename,
                size_bytes=document.size_bytes,
                mime_type=document.mime_type,
                created_at=document.created_at,
                metadata=document.metadata,
                job_id=None,
                task_id=None,
                ingestion_status="failed_to_start"
            )
    
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Get document by ID"""
    try:
        document = await doc_service.get_document(doc_id, tenant_id)
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            size_bytes=document.size_bytes,
            user_id=document.user_id,
            tenant_id=document.tenant_id,
            created_at=document.created_at,
            metadata=document.metadata
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    doc_service: DocumentService = Depends(get_document_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """List documents"""
    documents = await doc_service.list_documents(tenant_id, skip, limit)
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            size_bytes=doc.size_bytes,
            mime_type=doc.mime_type,
            user_id=doc.user_id,
            tenant_id=doc.tenant_id,
            created_at=doc.created_at,
            metadata=doc.metadata
        )
        for doc in documents
    ]


@router.get("/{doc_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Get chunks for document"""
    # Verify document exists
    await doc_service.get_document(doc_id, tenant_id)
    
    chunks = await doc_service.get_chunks(doc_id)
    
    return [
        ChunkResponse(
            id=chunk.id,
            doc_id=chunk.doc_id,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            position=chunk.position,
            created_at=chunk.created_at
        )
        for chunk in chunks
    ]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Delete document"""
    success = await doc_service.delete_document(doc_id, tenant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"status": "deleted", "doc_id": doc_id}
