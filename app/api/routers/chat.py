"""
Chat/QA API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_chat_service, get_current_tenant_id
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatResponse, EvidenceResponse
from app.domain.models import RetrievalMode
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Chat/QA endpoint
    
    Supports multiple retrieval modes:
    - auto: Intelligent routing (GraphRAG → TextRAG fallback)
    - graph: GraphRAG only
    - text: TextRAG (BM25) only
    - hybrid: Combine both
    """
    try:
        # Parse mode
        mode = RetrievalMode(request.mode)
        
        # Generate answer
        answer = await chat_service.answer_question(
            question=request.question,
            tenant_id=tenant_id,
            mode=mode,
            doc_ids=request.doc_ids,
            top_k=request.top_k
        )
        
        return ChatResponse(
            answer=answer.answer,
            mode_used=answer.mode_used.value,
            confidence=answer.confidence,
            evidence=[
                EvidenceResponse(
                    doc_id=ev.doc_id,
                    chunk_id=ev.chunk_id,
                    page_start=ev.page_start,
                    page_end=ev.page_end,
                    snippet=ev.snippet,
                    score=ev.score,
                    source_type=ev.source_type
                )
                for ev in answer.evidence
            ],
            metadata=answer.metadata
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    except Exception as e:
        logger.exception("chat_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat request failed")
