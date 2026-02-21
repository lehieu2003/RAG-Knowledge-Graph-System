"""
Chat Service - Main orchestrator for Q&A
Coordinates retrieval + generation
"""
from typing import Optional, List

from app.services.retrieval_service import RetrievalService
from app.services.generation_service import GenerationService
from app.domain.models import RetrievalMode, GeneratedAnswer
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Chat/QA orchestrator"""
    
    def __init__(
        self,
        retrieval_service: RetrievalService,
        generation_service: GenerationService
    ):
        self.retrieval_service = retrieval_service
        self.generation_service = generation_service
    
    async def answer_question(
        self,
        question: str,
        tenant_id: str,
        mode: RetrievalMode = RetrievalMode.AUTO,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> GeneratedAnswer:
        """
        End-to-end Q&A: retrieve + generate
        
        Args:
            question: User question
            tenant_id: Tenant for isolation
            mode: Retrieval strategy (auto/graph/text/hybrid)
            doc_ids: Optional document filter
            top_k: Number of evidence pieces to retrieve
        
        Returns:
            Generated answer with citations
        """
        logger.info(
            "chat_request",
            question=question[:100],
            mode=mode.value,
            tenant_id=tenant_id
        )
        
        # Step 1: Retrieval
        retrieval_result = await self.retrieval_service.retrieve(
            question=question,
            tenant_id=tenant_id,
            mode=mode,
            doc_ids=doc_ids,
            top_k=top_k
        )
        
        logger.info(
            "retrieval_completed",
            mode=retrieval_result.mode_used.value,
            evidence_count=len(retrieval_result.evidence),
            confidence=retrieval_result.confidence
        )
        
        # Step 2: Generation
        answer = await self.generation_service.generate_answer(
            question=question,
            evidence=retrieval_result.evidence,
            mode_used=retrieval_result.mode_used,
            retrieval_confidence=retrieval_result.confidence
        )
        
        logger.info(
            "chat_completed",
            mode=answer.mode_used.value,
            confidence=answer.confidence
        )
        
        return answer
