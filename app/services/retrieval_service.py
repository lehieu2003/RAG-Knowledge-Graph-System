"""
Retrieval Service - Orchestrates GraphRAG + TextRAG
Hybrid routing with confidence scoring
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from app.domain.ports import KnowledgeGraphRepository, TextIndexRepository
from app.domain.models import Evidence, RetrievalMode, GraphPath
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RetrievalResult:
    """Retrieval result with mode and confidence"""
    evidence: List[Evidence]
    mode_used: RetrievalMode
    confidence: float
    metadata: Dict[str, Any]


class RetrievalService:
    """Unified retrieval service with routing"""
    
    def __init__(
        self,
        kg_repo: KnowledgeGraphRepository,
        text_index: TextIndexRepository
    ):
        self.kg_repo = kg_repo
        self.text_index = text_index
    
    async def retrieve(
        self,
        question: str,
        tenant_id: str,
        mode: RetrievalMode = RetrievalMode.AUTO,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> RetrievalResult:
        """
        Unified retrieval with automatic mode selection
        
        Mode selection logic:
        - AUTO: Try GraphRAG first, fallback to TextRAG
        - GRAPH: GraphRAG only
        - TEXT: TextRAG only
        - HYBRID: Combine both
        """
        if mode == RetrievalMode.GRAPH:
            return await self._retrieve_graph(question, tenant_id, doc_ids, top_k)
        
        elif mode == RetrievalMode.TEXT:
            return await self._retrieve_text(question, tenant_id, doc_ids, top_k)
        
        elif mode == RetrievalMode.HYBRID:
            return await self._retrieve_hybrid(question, tenant_id, doc_ids, top_k)
        
        else:  # AUTO
            return await self._retrieve_auto(question, tenant_id, doc_ids, top_k)
    
    async def _retrieve_auto(
        self,
        question: str,
        tenant_id: str,
        doc_ids: Optional[List[str]],
        top_k: int
    ) -> RetrievalResult:
        """Auto mode: Try graph, fallback to text"""
        # Try GraphRAG
        graph_result = await self._retrieve_graph(question, tenant_id, doc_ids, top_k)
        
        # Evaluate confidence
        if graph_result.confidence >= settings.graph_confidence_threshold:
            logger.info("retrieval_mode_selected", mode="graph", confidence=graph_result.confidence)
            return graph_result
        
        # Fallback to TextRAG
        logger.info("retrieval_fallback_to_text", graph_confidence=graph_result.confidence)
        text_result = await self._retrieve_text(question, tenant_id, doc_ids, top_k)
        return text_result
    
    async def _retrieve_graph(
        self,
        question: str,
        tenant_id: str,
        doc_ids: Optional[List[str]],
        top_k: int
    ) -> RetrievalResult:
        """GraphRAG: Entity resolution + traversal"""
        # Step 1: Resolve anchor entities from question
        anchor_entities = await self._resolve_anchors(question, tenant_id)
        
        if not anchor_entities:
            return RetrievalResult(
                evidence=[],
                mode_used=RetrievalMode.GRAPH,
                confidence=0.0,
                metadata={"reason": "no_anchors"}
            )
        
        anchor_ids = [e.id for e in anchor_entities]
        
        # Step 2: Traverse graph
        paths = await self.kg_repo.traverse_graph(
            anchor_ids=anchor_ids,
            hop_limit=settings.graph_hop_limit,
            tenant_id=tenant_id
        )
        
        # Step 3: Score paths and convert to evidence
        evidence = self._paths_to_evidence(paths, doc_ids)
        
        # Step 4: Compute confidence
        confidence = self._compute_graph_confidence(anchor_entities, paths)
        
        return RetrievalResult(
            evidence=evidence[:top_k],
            mode_used=RetrievalMode.GRAPH,
            confidence=confidence,
            metadata={
                "anchors": len(anchor_entities),
                "paths": len(paths)
            }
        )
    
    async def _retrieve_text(
        self,
        question: str,
        tenant_id: str,
        doc_ids: Optional[List[str]],
        top_k: int
    ) -> RetrievalResult:
        """TextRAG: BM25 search"""
        evidence = await self.text_index.search(
            query=question,
            tenant_id=tenant_id,
            doc_ids=doc_ids,
            top_k=top_k
        )
        
        # Compute confidence based on scores
        confidence = self._compute_text_confidence(evidence)
        
        return RetrievalResult(
            evidence=evidence,
            mode_used=RetrievalMode.TEXT,
            confidence=confidence,
            metadata={"results": len(evidence)}
        )
    
    async def _retrieve_hybrid(
        self,
        question: str,
        tenant_id: str,
        doc_ids: Optional[List[str]],
        top_k: int
    ) -> RetrievalResult:
        """Hybrid: Combine graph and text"""
        # Get both
        graph_result = await self._retrieve_graph(question, tenant_id, doc_ids, top_k)
        text_result = await self._retrieve_text(question, tenant_id, doc_ids, top_k)
        
        # Combine and re-rank (simple: interleave)
        combined_evidence = self._combine_evidence(
            graph_result.evidence,
            text_result.evidence,
            top_k
        )
        
        # Average confidence
        confidence = (graph_result.confidence + text_result.confidence) / 2
        
        return RetrievalResult(
            evidence=combined_evidence,
            mode_used=RetrievalMode.HYBRID,
            confidence=confidence,
            metadata={
                "graph_evidence": len(graph_result.evidence),
                "text_evidence": len(text_result.evidence)
            }
        )
    
    async def _resolve_anchors(
        self,
        question: str,
        tenant_id: str
    ) -> List[Any]:
        """Resolve anchor entities from question"""
        # Simple approach: extract keywords and fuzzy match
        keywords = self._extract_keywords(question)
        
        anchors = []
        for keyword in keywords:
            matches = await self.kg_repo.find_entities_fuzzy(
                query=keyword,
                tenant_id=tenant_id,
                limit=3
            )
            anchors.extend(matches)
        
        # Deduplicate
        seen_ids = set()
        unique_anchors = []
        for anchor in anchors:
            if anchor.id not in seen_ids:
                seen_ids.add(anchor.id)
                unique_anchors.append(anchor)
        
        return unique_anchors[:5]  # Top 5 anchors
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract keywords from question (simple approach)"""
        # Remove stop words and short words
        stop_words = {"what", "why", "how", "when", "where", "who", "is", "are", "the", "a", "an", "in", "on", "at", "to", "for"}
        words = question.lower().split()
        keywords = [w.strip("?.,!") for w in words if w not in stop_words and len(w) > 3]
        return keywords[:5]
    
    def _paths_to_evidence(
        self,
        paths: List[GraphPath],
        doc_filter: Optional[List[str]]
    ) -> List[Evidence]:
        """Convert graph paths to evidence objects"""
        evidence_list = []
        
        for path in paths:
            for prov in path.provenance:
                # Filter by doc_ids if provided
                if doc_filter and prov["doc_id"] not in doc_filter:
                    continue
                
                # Create snippet from path
                snippet = f"Path: {' -> '.join(path.entities[:3])}... (Confidence: {path.confidence:.2f})"
                
                evidence_list.append(Evidence(
                    chunk_id=prov["chunk_id"],
                    doc_id=prov["doc_id"],
                    page_start=prov["page_start"],
                    page_end=prov["page_end"],
                    snippet=snippet,
                    score=path.confidence,
                    source_type="graph",
                    metadata={"path": path.entities, "relations": path.relations}
                ))
        
        return evidence_list
    
    def _compute_graph_confidence(self, anchors: List, paths: List[GraphPath]) -> float:
        """Compute confidence for graph retrieval"""
        if not anchors or not paths:
            return 0.0
        
        # Factors: anchor quality, path count, average path confidence
        anchor_factor = min(len(anchors) / 3, 1.0)  # Ideal: 3+ anchors
        path_factor = min(len(paths) / 5, 1.0)  # Ideal: 5+ paths
        
        if paths:
            avg_path_conf = sum(p.confidence for p in paths) / len(paths)
        else:
            avg_path_conf = 0.0
        
        confidence = (anchor_factor * 0.3 + path_factor * 0.3 + avg_path_conf * 0.4)
        return confidence
    
    def _compute_text_confidence(self, evidence: List[Evidence]) -> float:
        """Compute confidence for text retrieval"""
        if not evidence:
            return 0.0
        
        # Use top score as indicator
        top_score = evidence[0].score if evidence else 0.0
        
        # Normalize (BM25 scores can vary widely)
        confidence = min(top_score / 10, 1.0)  # Rough normalization
        return confidence
    
    def _combine_evidence(
        self,
        graph_evidence: List[Evidence],
        text_evidence: List[Evidence],
        top_k: int
    ) -> List[Evidence]:
        """Combine and interleave evidence"""
        combined = []
        
        # Interleave
        max_len = max(len(graph_evidence), len(text_evidence))
        for i in range(max_len):
            if i < len(graph_evidence):
                combined.append(graph_evidence[i])
            if i < len(text_evidence):
                combined.append(text_evidence[i])
        
        return combined[:top_k]
