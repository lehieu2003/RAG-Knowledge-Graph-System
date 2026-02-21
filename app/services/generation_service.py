"""
Generation Service - Grounded answer generation
Deterministic citations (no LLM hallucination)
"""
from typing import List, Dict, Any
import json

from app.domain.ports import LLMClient
from app.domain.models import Evidence, GeneratedAnswer, RetrievalMode
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import GenerationError
from app.llm.prompts import QA_WITH_EVIDENCE_PROMPT, build_evidence_blocks

logger = get_logger(__name__)
settings = get_settings()


class GenerationService:
    """Answer generation with grounded citations"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def generate_answer(
        self,
        question: str,
        evidence: List[Evidence],
        mode_used: RetrievalMode,
        retrieval_confidence: float
    ) -> GeneratedAnswer:
        """
        Generate grounded answer with deterministic citations
        
        Critical: LLM only selects which evidence to use, NOT the citations themselves
        """
        if not evidence:
            return GeneratedAnswer(
                answer="No relevant information found to answer the question.",
                mode_used=mode_used,
                confidence=0.0,
                evidence=[],
            )
        
        # Truncate evidence to fit context window
        evidence = self._truncate_evidence(evidence)
        
        # Build prompt
        evidence_blocks = build_evidence_blocks(evidence)
        prompt = QA_WITH_EVIDENCE_PROMPT.format(
            question=question,
            evidence_blocks=evidence_blocks
        )
        
        try:
            # Generate with LLM
            response = await self.llm_client.extract_structured(
                prompt,
                schema={"answer": "str", "evidence_used": "list", "confidence": "float"},
                max_tokens=settings.answer_max_tokens
            )
            
            # Parse response
            answer_text = response.get("answer", "")
            evidence_ids = response.get("evidence_used", [])
            llm_confidence = response.get("confidence", 0.5)
            
            # Map evidence IDs to actual evidence (deterministic citations)
            used_evidence = self._map_evidence_ids(evidence_ids, evidence)
            
            # Add deterministic citations to answer
            answer_with_citations = self._add_citations(answer_text, used_evidence)
            
            # Compute final confidence
            final_confidence = (retrieval_confidence * 0.6 + llm_confidence * 0.4)
            
            result = GeneratedAnswer(
                answer=answer_with_citations,
                mode_used=mode_used,
                confidence=final_confidence,
                evidence=used_evidence,
                metadata={
                    "retrieval_confidence": retrieval_confidence,
                    "llm_confidence": llm_confidence,
                }
            )
            
            logger.info(
                "answer_generated",
                mode=mode_used.value,
                confidence=final_confidence,
                evidence_used=len(used_evidence)
            )
            
            return result
        
        except Exception as e:
            logger.error("generation_failed", error=str(e))
            raise GenerationError(f"Answer generation failed: {e}")
    
    def _truncate_evidence(self, evidence: List[Evidence]) -> List[Evidence]:
        """Truncate evidence to fit context window"""
        max_length = settings.max_evidence_length
        current_length = 0
        truncated = []
        
        for ev in evidence:
            snippet_length = len(ev.snippet)
            if current_length + snippet_length > max_length:
                break
            current_length += snippet_length
            truncated.append(ev)
        
        return truncated
    
    def _map_evidence_ids(
        self,
        evidence_ids: List[str],
        all_evidence: List[Evidence]
    ) -> List[Evidence]:
        """Map evidence IDs (E1, E2, ...) to actual evidence objects"""
        mapped = []
        
        for eid in evidence_ids:
            # Extract number from E1, E2, etc.
            try:
                idx = int(eid.replace("E", "")) - 1  # E1 -> index 0
                if 0 <= idx < len(all_evidence):
                    mapped.append(all_evidence[idx])
            except (ValueError, IndexError):
                logger.warning("invalid_evidence_id", evidence_id=eid)
                continue
        
        return mapped
    
    def _add_citations(self, answer: str, evidence: List[Evidence]) -> str:
        """
        Add deterministic citations to answer
        
        Format: [Doc_ID, Page X]
        This ensures citations are accurate and not hallucinated
        """
        if not evidence:
            return answer
        
        # Build citation section
        citations = []
        for i, ev in enumerate(evidence, start=1):
            citation = f"[{i}] Document {ev.doc_id}, Page {ev.page_start}"
            if ev.page_end != ev.page_start:
                citation += f"-{ev.page_end}"
            citations.append(citation)
        
        # Append citations
        citation_section = "\n\n**Sources:**\n" + "\n".join(citations)
        return answer + citation_section
