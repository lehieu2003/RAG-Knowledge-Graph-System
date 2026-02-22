"""  
Ingestion Pipeline - Orchestrates full document processing
Idempotent, retryable, and observable
"""
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any

from app.domain.models import JobStatus, JobStep, Chunk
from app.core.logging import get_logger, set_correlation_id
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


def run_full_pipeline(job_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Run full ingestion pipeline (synchronous, called by Celery worker)
    
    Steps:
    1. EXTRACT_TEXT - Extract text from PDF
    2. CHUNK - Create chunks with page tracking
    3. EXTRACT_TRIPLES_REBEL - Extract with REBEL
    4. EXTRACT_TRIPLES_LLM - Extract with LLM
    5. UNION_POOL - Combine and deduplicate triples
    6. CANONICALIZE - Entity resolution
    7. UPSERT_GRAPH - Upload to Neo4j
    8. BUILD_TEXT_INDEX - Build BM25 index
    
    Returns:
        Result dict with stats
    """
    set_correlation_id(job_id)
    
    logger.info("ingestion_pipeline_started", job_id=job_id, tenant_id=tenant_id)
    
    # Initialize services (import here to avoid circular deps)
    from app.infra.postgres.database import AsyncSessionLocal
    from app.infra.postgres.repos import PostgresDocumentRepository, PostgresChunkRepository, PostgresJobRepository
    from app.infra.neo4j.repo import Neo4jKnowledgeGraphRepository
    from app.infra.neo4j.driver import init_neo4j, get_driver
    from app.infra.index.bm25 import FileBackedBM25Repository
    from app.services.document_service import DocumentService
    from app.services.ingestion_service import IngestionService
    from app.services.extraction_service import ExtractionService
    from app.services.canonicalization_service import CanonicalizationService
    from app.services.kg_service import KGService
    from app.llm.client import get_llm_client
    from app.utils.pdf import extract_text_from_pdf
    from app.utils.chunking import chunk_text_by_pages
    
    import asyncio
    
    async def _run_pipeline():
        # Ensure Neo4j is initialized
        try:
            get_driver()
        except RuntimeError:
            logger.info("neo4j_initializing", job_id=job_id)
            await init_neo4j()
        
        async with AsyncSessionLocal() as session:
            # Repos
            job_repo = PostgresJobRepository(session)
            doc_repo = PostgresDocumentRepository(session)
            chunk_repo = PostgresChunkRepository(session)
            kg_repo = Neo4jKnowledgeGraphRepository()
            text_index = FileBackedBM25Repository()
            
            # Services
            ingestion_service = IngestionService(job_repo)
            doc_service = DocumentService(doc_repo, chunk_repo)
            llm_client = get_llm_client()
            extraction_service = ExtractionService(llm_client)
            canon_service = CanonicalizationService()
            kg_service = KGService(kg_repo)
            
            # Get job
            try:
                job = await ingestion_service.get_job(job_id, tenant_id)
            except Exception as e:
                logger.error(
                    "job_not_found_in_db",
                    job_id=job_id,
                    tenant_id=tenant_id,
                    error=str(e),
                    hint="Job may not be committed to DB yet. Check transaction commit in API route."
                )
                raise
            
            document = await doc_service.get_document(job.doc_id, tenant_id)
            
            # Update status to running
            await ingestion_service.update_job_status(
                job_id, JobStatus.RUNNING, JobStep.EXTRACT_TEXT
            )
            
            stats = {}
            
            try:
                # Step 1: Extract text
                logger.info("step_extract_text_started", job_id=job_id)
                file_path = await doc_service.get_document_file_path(job.doc_id)
                extracted = extract_text_from_pdf(str(file_path))
                
                pages = extracted["pages"]
                stats["pages"] = len(pages)
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.EXTRACT_TEXT, "done", {"pages": len(pages)}
                )
                
                # Step 2: Chunk
                logger.info("step_chunk_started", job_id=job_id)
                await ingestion_service.update_job_status(
                    job_id, JobStatus.RUNNING, JobStep.CHUNK
                )
                
                chunk_results = chunk_text_by_pages(
                    pages,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap
                )
                
                # Create Chunk entities
                chunks = []
                for i, chunk_result in enumerate(chunk_results):
                    chunk = Chunk(
                        id=f"chunk_{uuid.uuid4().hex[:16]}",
                        doc_id=job.doc_id,
                        chunk_hash=chunk_result.chunk_hash,
                        text=chunk_result.text,
                        page_start=chunk_result.page_start,
                        page_end=chunk_result.page_end,
                        position=chunk_result.position,
                        user_id=job.user_id,
                        tenant_id=tenant_id,
                        created_at=datetime.utcnow(),
                    )
                    chunks.append(chunk)
                
                # Save chunks
                await chunk_repo.create_many(chunks)
                stats["chunks"] = len(chunks)
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.CHUNK, "done", {"chunks": len(chunks)}
                )
                
                # Step 3-4: Extract triples (hybrid)
                logger.info("step_extract_triples_started", job_id=job_id)
                await ingestion_service.update_job_status(
                    job_id, JobStatus.RUNNING, JobStep.EXTRACT_TRIPLES_REBEL
                )
                
                triples = await extraction_service.extract_triples_hybrid(
                    chunks, job.doc_id, use_rebel=True, use_llm=True
                )
                
                stats["triples_extracted"] = len(triples)
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.UNION_POOL, "done", {"triples": len(triples)}
                )
                
                # Step 5: Canonicalize
                logger.info("step_canonicalize_started", job_id=job_id)
                await ingestion_service.update_job_status(
                    job_id, JobStatus.RUNNING, JobStep.CANONICALIZE
                )
                
                entities, relations = await canon_service.canonicalize_triples(triples)
                
                stats["entities"] = len(entities)
                stats["relations"] = len(relations)
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.CANONICALIZE, "done", 
                    {"entities": len(entities), "relations": len(relations)}
                )
                
                # Step 6: Upsert graph
                logger.info("step_upsert_graph_started", job_id=job_id)
                await ingestion_service.update_job_status(
                    job_id, JobStatus.RUNNING, JobStep.UPSERT_GRAPH
                )
                
                kg_result = await kg_service.upsert_knowledge_graph(
                    entities, relations, tenant_id
                )
                
                stats["kg_result"] = kg_result
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.UPSERT_GRAPH, "done", kg_result
                )
                
                # Step 7: Build text index
                logger.info("step_build_index_started", job_id=job_id)
                await ingestion_service.update_job_status(
                    job_id, JobStatus.RUNNING, JobStep.BUILD_TEXT_INDEX
                )
                
                await text_index.index_chunks(chunks)
                
                await ingestion_service.update_job_progress(
                    job_id, JobStep.BUILD_TEXT_INDEX, "done", {"indexed": len(chunks)}
                )
                
                # Complete
                await ingestion_service.update_job_status(
                    job_id, JobStatus.DONE
                )
                
                logger.info("ingestion_pipeline_completed", job_id=job_id, stats=stats)
                
                return {
                    "status": "success",
                    "job_id": job_id,
                    "stats": stats
                }
            
            except Exception as e:
                logger.exception("ingestion_pipeline_failed", job_id=job_id, error=str(e))
                
                await ingestion_service.update_job_status(
                    job_id, JobStatus.FAILED, error_message=str(e)
                )
                
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "error": str(e)
                }
    
    # Run async pipeline with proper event loop handling
    # Always create a new event loop for Celery tasks to avoid thread conflicts
    try:
        # Check if we're in a thread with an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context - use asyncio.run
            raise RuntimeError("Already in async context")
        except RuntimeError:
            # Good - no running loop, we can create our own
            pass
        
        # Create fresh event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run_pipeline())
        finally:
            loop.close()
    except Exception as e:
        logger.error("event_loop_error", error=str(e))
        # Last resort: try asyncio.run with new loop
        return asyncio.run(_run_pipeline())
