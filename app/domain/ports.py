"""
Ports (interfaces) for dependency inversion
Abstract contracts that infrastructure implements
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.models import (
    Document, Chunk, IngestionJob, Triple, Entity, Relation,
    Evidence, GraphPath, JobStatus, JobStep
)


# ============ Repository Ports ============

class DocumentRepository(ABC):
    """Document persistence interface"""
    
    @abstractmethod
    async def create(self, document: Document) -> Document:
        pass
    
    @abstractmethod
    async def get_by_id(self, doc_id: str, tenant_id: str) -> Optional[Document]:
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Document]:
        pass
    
    @abstractmethod
    async def delete(self, doc_id: str, tenant_id: str) -> bool:
        pass


class ChunkRepository(ABC):
    """Chunk persistence interface"""
    
    @abstractmethod
    async def create_many(self, chunks: List[Chunk]) -> List[Chunk]:
        pass
    
    @abstractmethod
    async def get_by_doc_id(self, doc_id: str) -> List[Chunk]:
        pass
    
    @abstractmethod
    async def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        pass


class JobRepository(ABC):
    """Job persistence interface"""
    
    @abstractmethod
    async def create(self, job: IngestionJob) -> IngestionJob:
        pass
    
    @abstractmethod
    async def get_by_id(self, job_id: str, tenant_id: str) -> Optional[IngestionJob]:
        pass
    
    @abstractmethod
    async def update_status(
        self, 
        job_id: str, 
        status: JobStatus, 
        current_step: Optional[JobStep] = None,
        error_message: Optional[str] = None
    ) -> bool:
        pass
    
    @abstractmethod
    async def update_progress(self, job_id: str, progress: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: str, status: Optional[JobStatus] = None) -> List[IngestionJob]:
        pass


# ============ Knowledge Graph Port ============

class KnowledgeGraphRepository(ABC):
    """Neo4j graph operations interface"""
    
    @abstractmethod
    async def upsert_entity(self, entity: Entity, tenant_id: str) -> str:
        """Create or update entity, returns entity ID"""
        pass
    
    @abstractmethod
    async def upsert_relation(self, relation: Relation, tenant_id: str) -> bool:
        pass
    
    @abstractmethod
    async def batch_upsert(
        self, 
        entities: List[Entity], 
        relations: List[Relation],
        tenant_id: str
    ) -> Dict[str, int]:
        """Batch upsert, returns counts"""
        pass
    
    @abstractmethod
    async def find_entities_fuzzy(self, query: str, tenant_id: str, limit: int = 10) -> List[Entity]:
        """Fuzzy search entities"""
        pass
    
    @abstractmethod
    async def traverse_graph(
        self, 
        anchor_ids: List[str],
        hop_limit: int,
        tenant_id: str
    ) -> List[GraphPath]:
        """K-hop traversal from anchor entities"""
        pass
    
    @abstractmethod
    async def get_entity_neighborhood(self, entity_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get entity with immediate neighbors"""
        pass
    
    @abstractmethod
    async def verify_graph_stats(self, tenant_id: str) -> Dict[str, int]:
        """Get node/edge counts for verification"""
        pass


# ============ Text Index Port ============

class TextIndexRepository(ABC):
    """BM25 text index interface"""
    
    @abstractmethod
    async def index_chunks(self, chunks: List[Chunk]) -> bool:
        """Index chunk texts"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Evidence]:
        """BM25 search"""
        pass
    
    @abstractmethod
    async def delete_by_doc(self, doc_id: str) -> bool:
        """Remove document from index"""
        pass


# ============ LLM Port ============

class LLMClient(ABC):
    """LLM provider interface (OpenAI/Azure/Anthropic)"""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs
    ) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def extract_structured(
        self, 
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data (for triple extraction)"""
        pass


# ============ Embedding Port ============

class EmbeddingService(ABC):
    """Embedding model interface"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding"""
        pass
    
    @abstractmethod
    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Cosine similarity"""
        pass
