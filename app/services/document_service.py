"""
Document Service - Document management
Clean service with repository pattern
"""
import hashlib
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from app.domain.ports import DocumentRepository, ChunkRepository
from app.domain.models import Document, Chunk
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import DocumentNotFoundError, UploadError
from app.utils.pdf import extract_text_from_bytes, validate_pdf

logger = get_logger(__name__)
settings = get_settings()


class DocumentService:
    """Document management service"""
    
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository
    ):
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(
        self,
        filename: str,
        file_bytes: bytes,
        user_id: str,
        tenant_id: str,
        metadata: Optional[dict] = None
    ) -> Document:
        """
        Upload and store document
        
        Validates PDF, computes hash, stores file, creates DB record
        """
        # Validate
        if not validate_pdf(file_bytes):
            raise UploadError("Invalid PDF file")
        
        if len(file_bytes) > settings.max_upload_size:
            raise UploadError(f"File too large (max {settings.max_upload_size} bytes)")
        
        # Compute hash (for deduplication)
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Generate doc ID
        doc_id = f"doc_{uuid.uuid4().hex[:16]}"
        
        # Store file
        file_path = self.upload_dir / f"{doc_id}.pdf"
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # Create document entity
        document = Document(
            id=doc_id,
            filename=filename,
            content_hash=content_hash,
            size_bytes=len(file_bytes),
            mime_type="application/pdf",
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )
        
        # Persist
        await self.doc_repo.create(document)
        
        logger.info("document_uploaded", doc_id=doc_id, filename=filename, size=len(file_bytes))
        return document
    
    async def get_document(self, doc_id: str, tenant_id: str) -> Document:
        """Get document by ID"""
        document = await self.doc_repo.get_by_id(doc_id, tenant_id)
        if not document:
            raise DocumentNotFoundError(doc_id)
        return document
    
    async def list_documents(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """List documents for tenant"""
        return await self.doc_repo.list_by_tenant(tenant_id, skip, limit)
    
    async def get_document_file_path(self, doc_id: str) -> Path:
        """Get file system path for document"""
        file_path = self.upload_dir / f"{doc_id}.pdf"
        if not file_path.exists():
            raise DocumentNotFoundError(doc_id)
        return file_path
    
    async def get_chunks(self, doc_id: str) -> List[Chunk]:
        """Get chunks for document"""
        return await self.chunk_repo.get_by_doc_id(doc_id)
    
    async def delete_document(self, doc_id: str, tenant_id: str) -> bool:
        """Delete document and associated data"""
        # Delete file
        file_path = self.upload_dir / f"{doc_id}.pdf"
        if file_path.exists():
            file_path.unlink()
        
        # Delete DB record
        result = await self.doc_repo.delete(doc_id, tenant_id)
        
        logger.info("document_deleted", doc_id=doc_id)
        return result
