"""
Knowledge Graph Service - High-level KG operations
Wrapper around KG repository with business logic
"""
from typing import List, Dict, Any

from app.domain.ports import KnowledgeGraphRepository
from app.domain.models import Entity, Relation
from app.core.logging import get_logger

logger = get_logger(__name__)


class KGService:
    """Knowledge graph service"""
    
    def __init__(self, kg_repo: KnowledgeGraphRepository):
        self.kg_repo = kg_repo
    
    async def upsert_knowledge_graph(
        self,
        entities: List[Entity],
        relations: List[Relation],
        tenant_id: str
    ) -> Dict[str, int]:
        """
        Upsert entities and relations (idempotent)
        
        Returns:
            Counts of created/updated entities and relations
        """
        if not entities and not relations:
            return {"entities": 0, "relations": 0}
        
        logger.info(
            "kg_upsert_started",
            entities=len(entities),
            relations=len(relations),
            tenant_id=tenant_id
        )
        
        # Batch upsert
        result = await self.kg_repo.batch_upsert(entities, relations, tenant_id)
        
        logger.info("kg_upsert_completed", result=result)
        return result
    
    async def search_entities(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10
    ) -> List[Entity]:
        """Fuzzy search entities"""
        return await self.kg_repo.find_entities_fuzzy(query, tenant_id, limit)
    
    async def get_entity_details(
        self,
        entity_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get entity with neighborhood"""
        return await self.kg_repo.get_entity_neighborhood(entity_id, tenant_id)
    
    async def get_stats(self, tenant_id: str) -> Dict[str, int]:
        """Get graph statistics"""
        return await self.kg_repo.verify_graph_stats(tenant_id)
    
    async def initialize_schema(self):
        """Initialize Neo4j constraints (call on startup)"""
        await self.kg_repo.create_constraints()
    
    def upsert_knowledge_graph_sync(
        self,
        entities: List[Entity],
        relations: List[Relation],
        tenant_id: str
    ) -> Dict[str, int]:
        """
        Sync version for Celery tasks
        Avoids asyncio event loop conflicts in background workers
        """
        if not entities and not relations:
            return {"entities": 0, "relations": 0}
        
        logger.info(
            "kg_upsert_sync_started",
            entities=len(entities),
            relations=len(relations),
            tenant_id=tenant_id
        )
        
        # Batch upsert (sync)
        result = self.kg_repo.batch_upsert_sync(entities, relations, tenant_id)
        
        logger.info("kg_upsert_sync_completed", result=result)
        return result
