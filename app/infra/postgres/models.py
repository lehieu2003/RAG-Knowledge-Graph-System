"""
PostgreSQL database models using SQLAlchemy
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class JobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class DocumentModel(Base):
    """Documents table"""
    __tablename__ = "documents"
    
    id = Column(String(64), primary_key=True)
    filename = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(128), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    doc_metadata = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename})>"


class ChunkModel(Base):
    """Chunks table"""
    __tablename__ = "chunks"
    
    id = Column(String(64), primary_key=True)
    doc_id = Column(String(64), nullable=False, index=True)
    chunk_hash = Column(String(64), nullable=False, unique=True)
    text = Column(Text, nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.doc_id}, position={self.position})>"


class IngestionJobModel(Base):
    """Ingestion jobs table"""
    __tablename__ = "ingestion_jobs"
    
    id = Column(String(64), primary_key=True)
    doc_id = Column(String(64), nullable=False, index=True)
    status = Column(SQLEnum(JobStatusEnum), nullable=False, default=JobStatusEnum.PENDING, index=True)
    current_step = Column(String(64), nullable=True)
    progress = Column(JSON, default={})
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<IngestionJob(id={self.id}, status={self.status})>"


class AuditLogModel(Base):
    """Audit trail (optional but recommended for production)"""
    __tablename__ = "audit_logs"
    
    id = Column(String(64), primary_key=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    details = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AuditLog(entity_type={self.entity_type}, action={self.action})>"
