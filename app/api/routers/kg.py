"""
Knowledge Graph API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.api.deps import get_kg_service, get_current_tenant_id
from app.services.kg_service import KGService
from app.schemas.kg import (
    EntitySearchRequest,
    EntitySearchResponse,
    EntityResponse,
    EntityDetailResponse,
    GraphStatsResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/kg", tags=["knowledge_graph"])


@router.post("/entities/search", response_model=List[EntityResponse])
async def search_entities(
    request: EntitySearchRequest,
    kg_service: KGService = Depends(get_kg_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Search entities by name"""
    entities = await kg_service.search_entities(
        query=request.query,
        tenant_id=tenant_id,
        limit=request.limit
    )
    
    return [
        EntityResponse(
            id=entity.id,
            canonical_name=entity.canonical_name,
            entity_type=entity.entity_type,
            aliases=entity.aliases,
            metadata=entity.metadata
        )
        for entity in entities
    ]


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_details(
    entity_id: str,
    kg_service: KGService = Depends(get_kg_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Get entity with neighborhood"""
    details = await kg_service.get_entity_details(entity_id, tenant_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return EntityDetailResponse(
        id=details["id"],
        name=details["name"],
        type=details["type"],
        aliases=details.get("aliases", []),
        neighbors=details.get("neighbors", [])
    )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    kg_service: KGService = Depends(get_kg_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Get graph statistics"""
    stats = await kg_service.get_stats(tenant_id)
    
    # Get document count from stats or default to 0
    doc_count = stats.get("document_count", 0)
    
    return GraphStatsResponse(
        entities=stats["entity_count"],
        relations=stats["relation_count"],
        documents=doc_count
    )
