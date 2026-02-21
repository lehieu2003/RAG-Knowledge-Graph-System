"""
Repository implementations for PostgreSQL
Concrete implementations of domain ports
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import DocumentRepository, ChunkRepository, JobRepository
from app.domain.models import Document, Chunk, IngestionJob, JobStatus, JobStep
from app.infra.postgres.models import DocumentModel, ChunkModel, IngestionJobModel
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostgresDocumentRepository(DocumentRepository):
    """PostgreSQL document repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, document: Document) -> Document:
        db_doc = DocumentModel(
            id=document.id,
            filename=document.filename,
            content_hash=document.content_hash,
            size_bytes=document.size_bytes,
            mime_type=document.mime_type,
            user_id=document.user_id,
            tenant_id=document.tenant_id,
            doc_metadata=document.metadata,
            created_at=document.created_at,
        )
        self.session.add(db_doc)
        await self.session.flush()
        return document
    
    async def get_by_id(self, doc_id: str, tenant_id: str) -> Optional[Document]:
        stmt = select(DocumentModel).where(
            DocumentModel.id == doc_id,
            DocumentModel.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        db_doc = result.scalar_one_or_none()
        
        if not db_doc:
            return None
        
        return Document(
            id=db_doc.id,
            filename=db_doc.filename,
            content_hash=db_doc.content_hash,
            size_bytes=db_doc.size_bytes,
            mime_type=db_doc.mime_type,
            user_id=db_doc.user_id,
            tenant_id=db_doc.tenant_id,
            metadata=db_doc.doc_metadata,
            created_at=db_doc.created_at,
        )
    
    async def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Document]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.tenant_id == tenant_id)
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        db_docs = result.scalars().all()
        
        return [
            Document(
                id=doc.id,
                filename=doc.filename,
                content_hash=doc.content_hash,
                size_bytes=doc.size_bytes,
                mime_type=doc.mime_type,
                user_id=doc.user_id,
                tenant_id=doc.tenant_id,
                metadata=doc.doc_metadata,
                created_at=doc.created_at,
            )
            for doc in db_docs
        ]
    
    async def delete(self, doc_id: str, tenant_id: str) -> bool:
        stmt = delete(DocumentModel).where(
            DocumentModel.id == doc_id,
            DocumentModel.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0


class PostgresChunkRepository(ChunkRepository):
    """PostgreSQL chunk repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_many(self, chunks: List[Chunk]) -> List[Chunk]:
        db_chunks = [
            ChunkModel(
                id=chunk.id,
                doc_id=chunk.doc_id,
                chunk_hash=chunk.chunk_hash,
                text=chunk.text,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                position=chunk.position,
                user_id=chunk.user_id,
                tenant_id=chunk.tenant_id,
                created_at=chunk.created_at,
            )
            for chunk in chunks
        ]
        self.session.add_all(db_chunks)
        await self.session.flush()
        return chunks
    
    async def get_by_doc_id(self, doc_id: str) -> List[Chunk]:
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.doc_id == doc_id)
            .order_by(ChunkModel.position)
        )
        result = await self.session.execute(stmt)
        db_chunks = result.scalars().all()
        
        return [
            Chunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                chunk_hash=chunk.chunk_hash,
                text=chunk.text,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                position=chunk.position,
                user_id=chunk.user_id,
                tenant_id=chunk.tenant_id,
                created_at=chunk.created_at,
            )
            for chunk in db_chunks
        ]
    
    async def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        stmt = select(ChunkModel).where(ChunkModel.id == chunk_id)
        result = await self.session.execute(stmt)
        db_chunk = result.scalar_one_or_none()
        
        if not db_chunk:
            return None
        
        return Chunk(
            id=db_chunk.id,
            doc_id=db_chunk.doc_id,
            chunk_hash=db_chunk.chunk_hash,
            text=db_chunk.text,
            page_start=db_chunk.page_start,
            page_end=db_chunk.page_end,
            position=db_chunk.position,
            user_id=db_chunk.user_id,
            tenant_id=db_chunk.tenant_id,
            created_at=db_chunk.created_at,
        )


class PostgresJobRepository(JobRepository):
    """PostgreSQL job repository"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, job: IngestionJob) -> IngestionJob:
        db_job = IngestionJobModel(
            id=job.id,
            doc_id=job.doc_id,
            status=job.status.value,
            current_step=job.current_step.value if job.current_step else None,
            progress=job.progress,
            user_id=job.user_id,
            tenant_id=job.tenant_id,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        self.session.add(db_job)
        await self.session.flush()
        return job
    
    async def get_by_id(self, job_id: str, tenant_id: str) -> Optional[IngestionJob]:
        stmt = select(IngestionJobModel).where(
            IngestionJobModel.id == job_id,
            IngestionJobModel.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        db_job = result.scalar_one_or_none()
        
        if not db_job:
            return None
        
        return IngestionJob(
            id=db_job.id,
            doc_id=db_job.doc_id,
            status=JobStatus(db_job.status.value),
            current_step=JobStep(db_job.current_step) if db_job.current_step else None,
            progress=db_job.progress,
            user_id=db_job.user_id,
            tenant_id=db_job.tenant_id,
            error_message=db_job.error_message,
            created_at=db_job.created_at,
            updated_at=db_job.updated_at,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
        )
    
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        current_step: Optional[JobStep] = None,
        error_message: Optional[str] = None
    ) -> bool:
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow(),
        }
        
        if current_step:
            update_data["current_step"] = current_step.value
        
        if error_message:
            update_data["error_message"] = error_message
        
        if status == JobStatus.RUNNING and current_step:
            update_data["started_at"] = datetime.utcnow()
        
        if status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELED):
            update_data["completed_at"] = datetime.utcnow()
        
        stmt = update(IngestionJobModel).where(
            IngestionJobModel.id == job_id
        ).values(**update_data)
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
    
    async def update_progress(self, job_id: str, progress: Dict[str, Any]) -> bool:
        stmt = update(IngestionJobModel).where(
            IngestionJobModel.id == job_id
        ).values(
            progress=progress,
            updated_at=datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
    
    async def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[JobStatus] = None
    ) -> List[IngestionJob]:
        stmt = select(IngestionJobModel).where(
            IngestionJobModel.tenant_id == tenant_id
        )
        
        if status:
            stmt = stmt.where(IngestionJobModel.status == status.value)
        
        stmt = stmt.order_by(IngestionJobModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        db_jobs = result.scalars().all()
        
        return [
            IngestionJob(
                id=job.id,
                doc_id=job.doc_id,
                status=JobStatus(job.status.value),
                current_step=JobStep(job.current_step) if job.current_step else None,
                progress=job.progress,
                user_id=job.user_id,
                tenant_id=job.tenant_id,
                error_message=job.error_message,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in db_jobs
        ]
