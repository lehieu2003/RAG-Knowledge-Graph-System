"""
Neo4j Knowledge Graph Repository Implementation
Production-ready with multi-tenancy, batch operations, and provenance
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.ports import KnowledgeGraphRepository
from app.domain.models import Entity, Relation, GraphPath
from app.core.logging import get_logger
from app.core.exceptions import GraphOperationError
from app.infra.neo4j.driver import get_neo4j_session, get_neo4j_session_sync
from app.infra.neo4j import cypher

logger = get_logger(__name__)


class Neo4jKnowledgeGraphRepository(KnowledgeGraphRepository):
    """Neo4j implementation of KG repository"""
    
    async def upsert_entity(self, entity: Entity, tenant_id: str) -> str:
        """Create or update entity"""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    cypher.UPSERT_ENTITY,
                    entity_id=entity.id,
                    tenant_id=tenant_id,
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type,
                    aliases=entity.aliases,
                    metadata=json.dumps(entity.metadata) if entity.metadata else "{}",
                )
                record = await result.single()
                return record["entity_id"]
        except Exception as e:
            logger.error("upsert_entity_failed", entity_id=entity.id, error=str(e))
            raise GraphOperationError("upsert_entity", str(e))
    
    async def upsert_relation(self, relation: Relation, tenant_id: str) -> bool:
        """Create or update relation"""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    cypher.UPSERT_RELATION,
                    tenant_id=tenant_id,
                    head_id=relation.head_id,
                    tail_id=relation.tail_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    extractor=relation.extractor.value,
                    doc_id=relation.doc_id,
                    chunk_id=relation.chunk_id,
                    page_start=relation.page_start,
                    page_end=relation.page_end,
                    span=relation.span,
                )
                record = await result.single()
                return record is not None
        except Exception as e:
            logger.error("upsert_relation_failed", error=str(e))
            raise GraphOperationError("upsert_relation", str(e))
    
    async def batch_upsert(
        self,
        entities: List[Entity],
        relations: List[Relation],
        tenant_id: str
    ) -> Dict[str, int]:
        """Batch upsert entities and relations"""
        try:
            async with get_neo4j_session() as session:
                # Batch entities
                entity_data = [
                    {
                        "id": e.id,
                        "canonical_name": e.canonical_name,
                        "entity_type": e.entity_type,
                        "aliases": e.aliases,
                        "metadata": json.dumps(e.metadata) if e.metadata else "{}",
                    }
                    for e in entities
                ]
                
                entity_result = await session.run(
                    cypher.BATCH_UPSERT_ENTITIES,
                    entities=entity_data,
                    tenant_id=tenant_id,
                )
                entity_record = await entity_result.single()
                entity_count = entity_record["count"]
                
                # Batch relations
                relation_data = [
                    {
                        "head_id": r.head_id,
                        "tail_id": r.tail_id,
                        "relation_type": r.relation_type,
                        "confidence": r.confidence,
                        "extractor": r.extractor.value,
                        "doc_id": r.doc_id,
                        "chunk_id": r.chunk_id,
                        "page_start": r.page_start,
                        "page_end": r.page_end,
                        "span": r.span,
                    }
                    for r in relations
                ]
                
                relation_result = await session.run(
                    cypher.BATCH_UPSERT_RELATIONS,
                    relations=relation_data,
                    tenant_id=tenant_id,
                )
                relation_record = await relation_result.single()
                relation_count = relation_record["count"]
                
                logger.info(
                    "graph_batch_upsert",
                    entities=entity_count,
                    relations=relation_count,
                    tenant_id=tenant_id,
                )
                
                return {
                    "entities": entity_count,
                    "relations": relation_count,
                }
        except Exception as e:
            logger.error("batch_upsert_failed", error=str(e))
            raise GraphOperationError("batch_upsert", str(e))
    
    async def find_entities_fuzzy(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10
    ) -> List[Entity]:
        """Fuzzy search entities"""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    cypher.FIND_ENTITIES_FUZZY,
                    search_query=query,
                    tenant_id=tenant_id,
                    limit=limit,
                )
                
                entities = []
                async for record in result:
                    # Parse metadata JSON string back to dict
                    metadata_str = record["metadata"]
                    metadata = {}
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    entities.append(Entity(
                        id=record["id"],
                        canonical_name=record["canonical_name"],
                        entity_type=record["entity_type"],
                        aliases=record["aliases"],
                        created_at=record["created_at"],
                        metadata=metadata,
                    ))
                
                return entities
        except Exception as e:
            logger.error("find_entities_fuzzy_failed", query=query, error=str(e))
            raise GraphOperationError("find_entities_fuzzy", str(e))
    
    async def traverse_graph(
        self,
        anchor_ids: List[str],
        hop_limit: int,
        tenant_id: str,
        min_confidence: float = 0.5,
    ) -> List[GraphPath]:
        """K-hop traversal from anchor entities"""
        try:
            async with get_neo4j_session() as session:
                # Generate query with hop_limit injected (Neo4j limitation)
                query = cypher.get_traverse_k_hop_query(hop_limit)
                
                result = await session.run(
                    query,
                    anchor_ids=anchor_ids,
                    tenant_id=tenant_id,
                    min_confidence=min_confidence,
                )
                
                paths = []
                async for record in result:
                    entities = [e["name"] for e in record["entities"]]
                    relations = [r["type"] for r in record["relations"]]
                    
                    # Collect provenance
                    provenance = []
                    for rel in record["relations"]:
                        provenance.append({
                            "doc_id": rel["doc_id"],
                            "chunk_id": rel["chunk_id"],
                            "page_start": rel["page_start"],
                            "page_end": rel["page_end"],
                        })
                    
                    # Compute path confidence (average of edge confidences)
                    confidences = [r["confidence"] for r in record["relations"]]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    
                    paths.append(GraphPath(
                        entities=entities,
                        relations=relations,
                        confidence=avg_confidence,
                        hop_count=record["hop_count"],
                        provenance=provenance,
                    ))
                
                return paths
        except Exception as e:
            logger.error("traverse_graph_failed", error=str(e))
            raise GraphOperationError("traverse_graph", str(e))
    
    async def get_entity_neighborhood(
        self,
        entity_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get entity with immediate neighbors"""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    cypher.GET_ENTITY_NEIGHBORHOOD,
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                )
                record = await result.single()
                
                if not record:
                    return {}
                
                return {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "aliases": record["aliases"],
                    "neighbors": record["neighbors"],
                }
        except Exception as e:
            logger.error("get_entity_neighborhood_failed", entity_id=entity_id, error=str(e))
            raise GraphOperationError("get_entity_neighborhood", str(e))
    
    async def verify_graph_stats(self, tenant_id: str) -> Dict[str, int]:
        """Get node/edge counts"""
        try:
            async with get_neo4j_session() as session:
                result = await session.run(
                    cypher.GET_GRAPH_STATS,
                    tenant_id=tenant_id,
                )
                record = await result.single()
                
                return {
                    "entity_count": record["entity_count"],
                    "relation_count": record["relation_count"],
                }
        except Exception as e:
            logger.error("verify_graph_stats_failed", error=str(e))
            raise GraphOperationError("verify_graph_stats", str(e))
    
    async def create_constraints(self):
        """Initialize schema constraints (call on startup)"""
        try:
            async with get_neo4j_session() as session:
                for query in cypher.CREATE_CONSTRAINTS:
                    await session.run(query)
                logger.info("neo4j_constraints_created")
        except Exception as e:
            logger.warning("create_constraints_failed", error=str(e))
    
    def batch_upsert_sync(
        self,
        entities: List[Entity],
        relations: List[Relation],
        tenant_id: str
    ) -> Dict[str, int]:
        """
        Sync version of batch upsert for Celery tasks
        Avoids asyncio event loop conflicts in background workers
        """
        try:
            with get_neo4j_session_sync() as session:
                # Batch entities
                entity_data = [
                    {
                        "id": e.id,
                        "canonical_name": e.canonical_name,
                        "entity_type": e.entity_type,
                        "aliases": e.aliases,
                        "metadata": json.dumps(e.metadata) if e.metadata else "{}",
                    }
                    for e in entities
                ]
                
                entity_result = session.run(
                    cypher.BATCH_UPSERT_ENTITIES,
                    entities=entity_data,
                    tenant_id=tenant_id,
                )
                entity_record = entity_result.single()
                entity_count = entity_record["count"]
                
                # Batch relations
                relation_data = [
                    {
                        "head_id": r.head_id,
                        "tail_id": r.tail_id,
                        "relation_type": r.relation_type,
                        "confidence": r.confidence,
                        "extractor": r.extractor.value,
                        "doc_id": r.doc_id,
                        "chunk_id": r.chunk_id,
                        "page_start": r.page_start,
                        "page_end": r.page_end,
                        "span": r.span,
                    }
                    for r in relations
                ]
                
                relation_result = session.run(
                    cypher.BATCH_UPSERT_RELATIONS,
                    relations=relation_data,
                    tenant_id=tenant_id,
                )
                relation_record = relation_result.single()
                relation_count = relation_record["count"]
                
                logger.info(
                    "graph_batch_upsert_sync",
                    entities=entity_count,
                    relations=relation_count,
                    tenant_id=tenant_id,
                )
                
                return {
                    "entities": entity_count,
                    "relations": relation_count,
                }
        except Exception as e:
            logger.error("batch_upsert_sync_failed", error=str(e))
            raise GraphOperationError("batch_upsert_sync", str(e))
    
    def create_constraints_sync(self):
        """Initialize schema constraints (sync version for Celery)"""
        try:
            with get_neo4j_session_sync() as session:
                for query in cypher.CREATE_CONSTRAINTS:
                    session.run(query)
                logger.info("neo4j_constraints_created_sync")
        except Exception as e:
            logger.warning("create_constraints_sync_failed", error=str(e))
