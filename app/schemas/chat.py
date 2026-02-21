"""
API schemas for chat/QA
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat/QA request"""
    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    mode: str = Field(default="auto", description="Retrieval mode: auto, graph, text, hybrid")
    doc_ids: Optional[List[str]] = Field(default=None, description="Optional document filter")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of evidence pieces to retrieve")


class EvidenceResponse(BaseModel):
    """Evidence piece"""
    doc_id: str
    chunk_id: str
    page_start: int
    page_end: int
    snippet: str
    score: float
    source_type: str  # "graph" or "text"


class ChatResponse(BaseModel):
    """Chat/QA response"""
    answer: str
    mode_used: str
    confidence: float
    evidence: List[EvidenceResponse]
    metadata: Dict[str, Any] = {}
