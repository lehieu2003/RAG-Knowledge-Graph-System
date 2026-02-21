"""
Domain models (internal business objects)
Clean separation from DB/API schemas
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


# ============ Enums ============

class JobStatus(str, Enum):
    """Ingestion job status"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class JobStep(str, Enum):
    """Pipeline steps"""
    EXTRACT_TEXT = "extract_text"
    CHUNK = "chunk"
    EXTRACT_TRIPLES_REBEL = "extract_triples_rebel"
    EXTRACT_TRIPLES_LLM = "extract_triples_llm"
    UNION_POOL = "union_pool"
    CANONICALIZE = "canonicalize"
    UPSERT_GRAPH = "upsert_graph"
    BUILD_TEXT_INDEX = "build_text_index"


class ExtractorType(str, Enum):
    """Extraction method"""
    REBEL = "rebel"
    LLM = "llm"


class RetrievalMode(str, Enum):
    """Retrieval strategy"""
    AUTO = "auto"
    GRAPH = "graph"
    TEXT = "text"
    HYBRID = "hybrid"


# ============ Document Domain ============

@dataclass
class Document:
    """Document entity"""
    id: str
    filename: str
    content_hash: str
    size_bytes: int
    mime_type: str
    user_id: str
    tenant_id: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Text chunk entity"""
    id: str
    doc_id: str
    chunk_hash: str
    text: str
    page_start: int
    page_end: int
    position: int
    user_id: str
    tenant_id: str
    created_at: datetime


# ============ Ingestion Domain ============

@dataclass
class IngestionJob:
    """Ingestion job entity"""
    id: str
    doc_id: str
    status: JobStatus
    current_step: Optional[JobStep]
    progress: Dict[str, Any]  # {step: {status, error, stats}}
    user_id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ============ Knowledge Graph Domain ============

@dataclass
class Entity:
    """Entity in knowledge graph"""
    id: str
    canonical_name: str
    entity_type: str
    aliases: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """Relation between entities"""
    head_id: str
    tail_id: str
    relation_type: str
    confidence: float
    extractor: ExtractorType
    doc_id: str
    chunk_id: str
    page_start: int
    page_end: int
    span: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Triple:
    """Extracted triple (raw)"""
    head: str
    relation: str
    tail: str
    confidence: float
    extractor: ExtractorType
    doc_id: str
    chunk_id: str
    page_start: int
    page_end: int
    span: Optional[str] = None
    
    def fingerprint(self) -> str:
        """Unique identifier for deduplication"""
        import hashlib
        content = f"{self.head}|{self.relation}|{self.tail}|{self.chunk_id}"
        return hashlib.sha256(content.encode()).hexdigest()


# ============ Retrieval Domain ============

@dataclass
class Evidence:
    """Retrieved evidence piece"""
    chunk_id: str
    doc_id: str
    page_start: int
    page_end: int
    snippet: str
    score: float
    source_type: str  # "graph" | "text"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """Graph traversal path"""
    entities: List[str]
    relations: List[str]
    confidence: float
    hop_count: int
    provenance: List[Dict[str, Any]]  # [{doc_id, chunk_id, page_start, page_end}]


# ============ Generation Domain ============

@dataclass
class GeneratedAnswer:
    """Generated answer with grounded citations"""
    answer: str
    mode_used: RetrievalMode
    confidence: float
    evidence: List[Evidence]
    metadata: Dict[str, Any] = field(default_factory=dict)
