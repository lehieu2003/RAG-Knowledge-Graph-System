"""
Custom exceptions with clear boundaries
Domain-specific errors for better error handling
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception"""
    
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


# Document & Ingestion Domain
class DocumentNotFoundError(AppException):
    """Document does not exist"""
    def __init__(self, doc_id: str):
        super().__init__(
            message=f"Document not found: {doc_id}",
            code="DOC_NOT_FOUND",
            status_code=404,
            details={"doc_id": doc_id}
        )


class InvalidDocumentError(AppException):
    """Invalid document format or content"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="INVALID_DOCUMENT",
            status_code=400,
            details=details
        )


class UploadError(AppException):
    """File upload failed"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="UPLOAD_ERROR",
            status_code=400,
            details=details
        )


# Ingestion Domain
class JobNotFoundError(AppException):
    """Ingestion job does not exist"""
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job not found: {job_id}",
            code="JOB_NOT_FOUND",
            status_code=404,
            details={"job_id": job_id}
        )


class JobExecutionError(AppException):
    """Job execution failed"""
    def __init__(self, job_id: str, step: str, reason: str):
        super().__init__(
            message=f"Job {job_id} failed at step {step}: {reason}",
            code="JOB_EXECUTION_ERROR",
            status_code=500,
            details={"job_id": job_id, "step": step, "reason": reason}
        )


# Extraction Domain
class ExtractionError(AppException):
    """Entity/relation extraction failed"""
    def __init__(self, message: str, extractor: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="EXTRACTION_ERROR",
            status_code=500,
            details={"extractor": extractor, **(details or {})}
        )


# Knowledge Graph Domain
class GraphOperationError(AppException):
    """Neo4j operation failed"""
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Graph operation '{operation}' failed: {reason}",
            code="GRAPH_ERROR",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


class EntityNotFoundError(AppException):
    """Entity does not exist in graph"""
    def __init__(self, entity_id: str):
        super().__init__(
            message=f"Entity not found: {entity_id}",
            code="ENTITY_NOT_FOUND",
            status_code=404,
            details={"entity_id": entity_id}
        )


# Retrieval Domain
class RetrievalError(AppException):
    """Retrieval operation failed"""
    def __init__(self, message: str, mode: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="RETRIEVAL_ERROR",
            status_code=500,
            details={"mode": mode, **(details or {})}
        )


# Generation Domain
class GenerationError(AppException):
    """LLM generation failed"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="GENERATION_ERROR",
            status_code=500,
            details=details
        )


class LLMProviderError(AppException):
    """LLM API provider error"""
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"LLM provider '{provider}' error: {reason}",
            code="LLM_PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider, "reason": reason}
        )


# Infrastructure
class DatabaseError(AppException):
    """Database operation failed"""
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database operation '{operation}' failed: {reason}",
            code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


class CacheError(AppException):
    """Cache operation failed"""
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Cache operation '{operation}' failed: {reason}",
            code="CACHE_ERROR",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


# Validation
class ValidationError(AppException):
    """Input validation failed"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field} if field else {}
        )
