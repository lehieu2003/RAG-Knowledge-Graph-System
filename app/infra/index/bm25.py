"""
BM25 Text Index Implementation
File-backed with Redis caching for production
"""
import pickle
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from rank_bm25 import BM25Okapi
import numpy as np

from app.domain.ports import TextIndexRepository
from app.domain.models import Evidence, Chunk
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import RetrievalError

logger = get_logger(__name__)
settings = get_settings()


class BM25Index:
    """BM25 index with document metadata"""
    
    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_tokens: List[List[str]] = []
        self.chunk_metadata: List[Dict[str, Any]] = []
        self.tenant_index: Dict[str, List[int]] = {}  # tenant_id -> chunk indices
    
    def build(self, chunks: List[Chunk], tenant_id: str):
        """Build or update index"""
        # Tokenize
        new_tokens = [self._tokenize(chunk.text) for chunk in chunks]
        new_metadata = [
            {
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "text": chunk.text,
                "tenant_id": chunk.tenant_id,
            }
            for chunk in chunks
        ]
        
        # Update corpus
        start_idx = len(self.corpus_tokens)
        self.corpus_tokens.extend(new_tokens)
        self.chunk_metadata.extend(new_metadata)
        
        # Update tenant index
        if tenant_id not in self.tenant_index:
            self.tenant_index[tenant_id] = []
        self.tenant_index[tenant_id].extend(
            range(start_idx, start_idx + len(new_tokens))
        )
        
        # Rebuild BM25
        self.bm25 = BM25Okapi(
            self.corpus_tokens,
            k1=settings.bm25_k1,
            b=settings.bm25_b
        )
    
    def search(
        self,
        query: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Evidence]:
        """BM25 search with tenant/doc filtering"""
        if not self.bm25:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Get scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Filter by tenant and optionally doc_ids
        valid_indices = self.tenant_index.get(tenant_id, [])
        if doc_ids:
            valid_indices = [
                idx for idx in valid_indices
                if self.chunk_metadata[idx]["doc_id"] in doc_ids
            ]
        
        # Get top-k from valid indices
        valid_scores = [(idx, scores[idx]) for idx in valid_indices]
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = valid_scores[:top_k]
        
        # Convert to Evidence
        evidence_list = []
        for idx, score in top_results:
            meta = self.chunk_metadata[idx]
            evidence_list.append(Evidence(
                chunk_id=meta["chunk_id"],
                doc_id=meta["doc_id"],
                page_start=meta["page_start"],
                page_end=meta["page_end"],
                snippet=meta["text"][:500],  # truncate
                score=float(score),
                source_type="text",
                metadata={"full_text": meta["text"]},
            ))
        
        return evidence_list
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (can be improved with spaCy/NLTK)"""
        return text.lower().split()
    
    def remove_doc(self, doc_id: str) -> bool:
        """Remove document from index (mark as deleted)"""
        # Mark chunks as deleted
        for i, meta in enumerate(self.chunk_metadata):
            if meta["doc_id"] == doc_id:
                meta["deleted"] = True
        
        # Remove from tenant index (rebuild tenant indices)
        for tenant_id in self.tenant_index:
            self.tenant_index[tenant_id] = [
                idx for idx in self.tenant_index[tenant_id]
                if not self.chunk_metadata[idx].get("deleted", False)
            ]
        
        return True


class FileBackedBM25Repository(TextIndexRepository):
    """File-backed BM25 repository with lazy loading"""
    
    def __init__(self, storage_dir: str = "./data/index"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "bm25_index.pkl"
        self.index: Optional[BM25Index] = None
        self._load_index()
    
    def _load_index(self):
        """Load index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "rb") as f:
                    self.index = pickle.load(f)
                logger.info("bm25_index_loaded", file=str(self.index_file))
            except Exception as e:
                logger.warning("bm25_index_load_failed", error=str(e))
                self.index = BM25Index()
        else:
            self.index = BM25Index()
    
    def _save_index(self):
        """Save index to disk"""
        try:
            with open(self.index_file, "wb") as f:
                pickle.dump(self.index, f)
            logger.info("bm25_index_saved")
        except Exception as e:
            logger.error("bm25_index_save_failed", error=str(e))
    
    async def index_chunks(self, chunks: List[Chunk]) -> bool:
        """Index chunks"""
        try:
            if not chunks:
                return True
            
            tenant_id = chunks[0].tenant_id
            self.index.build(chunks, tenant_id)
            self._save_index()
            
            logger.info("chunks_indexed", count=len(chunks), tenant_id=tenant_id)
            return True
        except Exception as e:
            logger.error("index_chunks_failed", error=str(e))
            raise RetrievalError(f"Failed to index chunks: {e}", "text")
    
    async def search(
        self,
        query: str,
        tenant_id: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Evidence]:
        """BM25 search"""
        try:
            return self.index.search(query, tenant_id, doc_ids, top_k)
        except Exception as e:
            logger.error("bm25_search_failed", query=query, error=str(e))
            raise RetrievalError(f"BM25 search failed: {e}", "text")
    
    async def delete_by_doc(self, doc_id: str) -> bool:
        """Remove document from index"""
        try:
            result = self.index.remove_doc(doc_id)
            self._save_index()
            return result
        except Exception as e:
            logger.error("delete_by_doc_failed", doc_id=doc_id, error=str(e))
            return False
