"""
API schemas for knowledge graph
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    """Entity details"""
    id: str
    canonical_name: str
    entity_type: str
    aliases: List[str] = []
    metadata: Dict[str, Any] = {}


class EntitySearchRequest(BaseModel):
    """Entity search request"""
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=100)


class EntitySearchResponse(BaseModel):
    """Entity search results"""
    entities: List[EntityResponse]
    count: int


class EntityDetailResponse(BaseModel):
    """Entity with neighborhood"""
    id: str
    name: str
    type: str
    aliases: List[str]
    neighbors: List[Dict[str, Any]]


class GraphStatsResponse(BaseModel):
    """Graph statistics"""
    entities: int
    relations: int
    documents: int
