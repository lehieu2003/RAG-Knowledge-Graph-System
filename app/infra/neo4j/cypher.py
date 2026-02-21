"""
Cypher query templates for knowledge graph operations
Production-ready with multi-tenancy and provenance
"""

# ============ Schema Constraints (run once on startup) ============

CREATE_CONSTRAINTS = [
    # Entity uniqueness per tenant
    """
    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
    FOR (e:Entity) REQUIRE (e.id, e.tenant_id) IS UNIQUE
    """,
    
    # Index for search
    """
    CREATE INDEX entity_name IF NOT EXISTS
    FOR (e:Entity) ON (e.canonical_name)
    """,
    
    """
    CREATE INDEX entity_tenant IF NOT EXISTS
    FOR (e:Entity) ON (e.tenant_id)
    """,
    
    # Document/Chunk indexes
    """
    CREATE INDEX doc_tenant IF NOT EXISTS
    FOR (d:Doc) ON (d.tenant_id)
    """,
    
    """
    CREATE INDEX chunk_tenant IF NOT EXISTS
    FOR (c:Chunk) ON (c.tenant_id)
    """,
]


# ============ Entity Operations ============

UPSERT_ENTITY = """
MERGE (e:Entity {id: $entity_id, tenant_id: $tenant_id})
ON CREATE SET
    e.canonical_name = $canonical_name,
    e.entity_type = $entity_type,
    e.aliases = $aliases,
    e.created_at = datetime(),
    e.metadata = $metadata
ON MATCH SET
    e.canonical_name = $canonical_name,
    e.entity_type = $entity_type,
    e.aliases = $aliases,
    e.metadata = $metadata
RETURN e.id as entity_id
"""


UPSERT_RELATION = """
MATCH (h:Entity {id: $head_id, tenant_id: $tenant_id})
MATCH (t:Entity {id: $tail_id, tenant_id: $tenant_id})
MERGE (h)-[r:RELATION {
    type: $relation_type,
    head_id: $head_id,
    tail_id: $tail_id,
    tenant_id: $tenant_id
}]->(t)
ON CREATE SET
    r.confidence = $confidence,
    r.extractor = $extractor,
    r.doc_id = $doc_id,
    r.chunk_id = $chunk_id,
    r.page_start = $page_start,
    r.page_end = $page_end,
    r.span = $span,
    r.created_at = datetime()
ON MATCH SET
    r.confidence = CASE 
        WHEN $confidence > r.confidence THEN $confidence 
        ELSE r.confidence 
    END
RETURN id(r) as rel_id
"""


# ============ Search Operations ============

FIND_ENTITIES_FUZZY = """
MATCH (e:Entity)
WHERE e.tenant_id = $tenant_id
  AND (
    toLower(e.canonical_name) CONTAINS toLower($search_query)
    OR any(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($search_query))
  )
RETURN e.id as id,
       e.canonical_name as canonical_name,
       e.entity_type as entity_type,
       e.aliases as aliases,
       e.created_at as created_at,
       e.metadata as metadata
ORDER BY size(e.canonical_name)
LIMIT $limit
"""


# ============ Graph Traversal ============

TRAVERSE_K_HOP = """
MATCH path = (anchor:Entity)-[r:RELATION*1..$hop_limit]-(connected:Entity)
WHERE anchor.id IN $anchor_ids
  AND anchor.tenant_id = $tenant_id
  AND connected.tenant_id = $tenant_id
  AND all(rel IN r WHERE rel.tenant_id = $tenant_id)
WITH path, relationships(path) as rels, nodes(path) as ns
WHERE all(rel IN rels WHERE rel.confidence >= $min_confidence)
RETURN 
  [n IN ns | {
    id: n.id, 
    name: n.canonical_name, 
    type: n.entity_type
  }] as entities,
  [rel IN rels | {
    type: rel.type,
    confidence: rel.confidence,
    doc_id: rel.doc_id,
    chunk_id: rel.chunk_id,
    page_start: rel.page_start,
    page_end: rel.page_end
  }] as relations,
  length(path) as hop_count
ORDER BY hop_count, size(rels) DESC
LIMIT 100
"""


GET_ENTITY_NEIGHBORHOOD = """
MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})
OPTIONAL MATCH (e)-[r:RELATION]-(neighbor:Entity)
WHERE r.tenant_id = $tenant_id
  AND neighbor.tenant_id = $tenant_id
RETURN 
  e.id as id,
  e.canonical_name as name,
  e.entity_type as type,
  e.aliases as aliases,
  collect(DISTINCT {
    id: neighbor.id,
    name: neighbor.canonical_name,
    type: neighbor.entity_type,
    relation: r.type,
    confidence: r.confidence,
    direction: CASE 
      WHEN startNode(r) = e THEN 'outgoing'
      ELSE 'incoming'
    END
  }) as neighbors
"""


# ============ Statistics & Verification ============

GET_GRAPH_STATS = """
MATCH (e:Entity {tenant_id: $tenant_id})
WITH count(e) as entity_count
MATCH ()-[r:RELATION {tenant_id: $tenant_id}]->()
RETURN entity_count, count(r) as relation_count
"""


# ============ Batch Operations ============

BATCH_UPSERT_ENTITIES = """
UNWIND $entities as entity
MERGE (e:Entity {id: entity.id, tenant_id: $tenant_id})
ON CREATE SET
    e.canonical_name = entity.canonical_name,
    e.entity_type = entity.entity_type,
    e.aliases = entity.aliases,
    e.created_at = datetime(),
    e.metadata = entity.metadata
ON MATCH SET
    e.canonical_name = entity.canonical_name,
    e.entity_type = entity.entity_type,
    e.aliases = entity.aliases,
    e.metadata = entity.metadata
RETURN count(e) as count
"""


BATCH_UPSERT_RELATIONS = """
UNWIND $relations as rel
MATCH (h:Entity {id: rel.head_id, tenant_id: $tenant_id})
MATCH (t:Entity {id: rel.tail_id, tenant_id: $tenant_id})
MERGE (h)-[r:RELATION {
    type: rel.relation_type,
    head_id: rel.head_id,
    tail_id: rel.tail_id,
    tenant_id: $tenant_id
}]->(t)
ON CREATE SET
    r.confidence = rel.confidence,
    r.extractor = rel.extractor,
    r.doc_id = rel.doc_id,
    r.chunk_id = rel.chunk_id,
    r.page_start = rel.page_start,
    r.page_end = rel.page_end,
    r.span = rel.span,
    r.created_at = datetime()
ON MATCH SET
    r.confidence = CASE 
        WHEN rel.confidence > r.confidence THEN rel.confidence 
        ELSE r.confidence 
    END
RETURN count(r) as count
"""


# ============ Cleanup ============

DELETE_DOCUMENT_GRAPH = """
MATCH (d:Doc {id: $doc_id, tenant_id: $tenant_id})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
OPTIONAL MATCH ()-[r:RELATION]->()
WHERE r.doc_id = $doc_id AND r.tenant_id = $tenant_id
DELETE r
WITH d, collect(c) as chunks
DELETE chunks, d
RETURN count(d) as deleted
"""
