"""
Canonicalization Service - Entity resolution
Clustering-based canonicalization with embeddings
"""
from typing import List, Dict, Tuple
from collections import defaultdict
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sentence_transformers import SentenceTransformer

from app.domain.models import Triple, Entity
from app.domain.ports import EmbeddingService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.text import normalize_entity_name
import uuid

logger = get_logger(__name__)
settings = get_settings()


class CanonicalizationService:
    """Entity canonicalization using embeddings + clustering"""
    
    def __init__(self):
        self.embedding_model = None  # Lazy load
    
    def _load_model(self):
        """Lazy load embedding model"""
        if self.embedding_model is None:
            logger.info("loading_embedding_model", model=settings.embedding_model)
            self.embedding_model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device
            )
            logger.info("embedding_model_loaded")
    
    async def canonicalize_triples(
        self,
        triples: List[Triple]
    ) -> Tuple[List[Entity], List[Triple]]:
        """
        Canonicalize entities in triples
        
        Returns:
            (canonical_entities, rewritten_triples)
        """
        if not triples:
            return [], []
        
        # Extract unique entity names
        entity_names = set()
        for triple in triples:
            entity_names.add(triple.head)
            entity_names.add(triple.tail)
        
        entity_names = list(entity_names)
        logger.info("canonicalization_started", entities=len(entity_names))
        
        # Build alias -> canonical mapping
        alias_to_canonical = await self._build_alias_mapping(entity_names)
        
        # Create Entity objects
        canonical_entities = self._create_entities(alias_to_canonical)
        
        # Rewrite triples with canonical IDs
        rewritten_triples = self._rewrite_triples(triples, alias_to_canonical)
        
        logger.info(
            "canonicalization_completed",
            entities=len(canonical_entities),
            triples=len(rewritten_triples)
        )
        
        return canonical_entities, rewritten_triples
    
    async def _build_alias_mapping(
        self,
        entity_names: List[str]
    ) -> Dict[str, Dict]:
        """
        Build alias -> canonical mapping using clustering
        
        Returns:
            {alias: {"canonical": str, "id": str, "type": str}}
        """
        self._load_model()
        
        # Normalize names
        normalized = [normalize_entity_name(name) for name in entity_names]
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(
            normalized,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        # Cluster with threshold
        threshold = settings.entity_similarity_threshold
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - threshold,  # convert similarity to distance
            linkage='average',
            metric='cosine'
        )
        
        labels = clustering.fit_predict(embeddings)
        
        # Build clusters
        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[label].append((entity_names[idx], normalized[idx]))
        
        # Build mapping
        alias_mapping = {}
        
        for cluster_id, members in clusters.items():
            # Choose canonical name (shortest, most common)
            canonical = min(members, key=lambda x: len(x[0]))[0]
            entity_id = f"ent_{uuid.uuid4().hex[:16]}"
            entity_type = "ENTITY"  # Can be enhanced with NER
            
            for original_name, _ in members:
                alias_mapping[original_name] = {
                    "canonical": canonical,
                    "id": entity_id,
                    "type": entity_type,
                    "aliases": [m[0] for m in members]
                }
        
        logger.info("alias_mapping_built", clusters=len(clusters), aliases=len(alias_mapping))
        return alias_mapping
    
    def _create_entities(self, alias_mapping: Dict[str, Dict]) -> List[Entity]:
        """Create Entity objects from alias mapping"""
        # Group by canonical ID
        entity_groups = defaultdict(lambda: {"canonical": None, "aliases": set(), "type": None})
        
        for alias, info in alias_mapping.items():
            ent_id = info["id"]
            entity_groups[ent_id]["canonical"] = info["canonical"]
            entity_groups[ent_id]["aliases"].update(info["aliases"])
            entity_groups[ent_id]["type"] = info["type"]
        
        # Create entities
        entities = []
        for ent_id, data in entity_groups.items():
            entities.append(Entity(
                id=ent_id,
                canonical_name=data["canonical"],
                entity_type=data["type"],
                aliases=list(data["aliases"]),
            ))
        
        return entities
    
    def _rewrite_triples(
        self,
        triples: List[Triple],
        alias_mapping: Dict[str, Dict]
    ) -> List[Triple]:
        """Rewrite triples with canonical entity IDs"""
        # Create mapping: (canonical_id, canonical_name) for heads and tails
        from app.domain.models import Relation
        
        relations = []
        
        for triple in triples:
            head_info = alias_mapping.get(triple.head)
            tail_info = alias_mapping.get(triple.tail)
            
            if not head_info or not tail_info:
                continue
            
            # Create Relation with canonical IDs
            relation = Relation(
                head_id=head_info["id"],
                tail_id=tail_info["id"],
                relation_type=triple.relation,
                confidence=triple.confidence,
                extractor=triple.extractor,
                doc_id=triple.doc_id,
                chunk_id=triple.chunk_id,
                page_start=triple.page_start,
                page_end=triple.page_end,
                span=triple.span,
            )
            
            relations.append(relation)
        
        return relations
