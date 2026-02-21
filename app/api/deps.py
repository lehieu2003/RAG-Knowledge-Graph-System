"""
Dependency injection for FastAPI
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.postgres.database import get_db
from app.infra.postgres.repos import (
    PostgresDocumentRepository,
    PostgresChunkRepository,
    PostgresJobRepository
)
from app.infra.neo4j.repo import Neo4jKnowledgeGraphRepository
from app.infra.index.bm25 import FileBackedBM25Repository
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.extraction_service import ExtractionService
from app.services.canonicalization_service import CanonicalizationService
from app.services.kg_service import KGService
from app.services.retrieval_service import RetrievalService
from app.services.generation_service import GenerationService
from app.services.chat_service import ChatService
from app.llm.client import get_llm_client
from app.core.auth import get_current_user_id, get_current_tenant_id


# ============ Repository Dependencies ============

def get_doc_repo(db: AsyncSession = Depends(get_db)) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(db)


def get_chunk_repo(db: AsyncSession = Depends(get_db)) -> PostgresChunkRepository:
    return PostgresChunkRepository(db)


def get_job_repo(db: AsyncSession = Depends(get_db)) -> PostgresJobRepository:
    return PostgresJobRepository(db)


def get_kg_repo() -> Neo4jKnowledgeGraphRepository:
    return Neo4jKnowledgeGraphRepository()


def get_text_index() -> FileBackedBM25Repository:
    return FileBackedBM25Repository()


# ============ Service Dependencies ============

def get_document_service(
    doc_repo: PostgresDocumentRepository = Depends(get_doc_repo),
    chunk_repo: PostgresChunkRepository = Depends(get_chunk_repo)
) -> DocumentService:
    return DocumentService(doc_repo, chunk_repo)


def get_ingestion_service(
    job_repo: PostgresJobRepository = Depends(get_job_repo)
) -> IngestionService:
    return IngestionService(job_repo)


def get_kg_service(
    kg_repo: Neo4jKnowledgeGraphRepository = Depends(get_kg_repo)
) -> KGService:
    return KGService(kg_repo)


def get_retrieval_service(
    kg_repo: Neo4jKnowledgeGraphRepository = Depends(get_kg_repo),
    text_index: FileBackedBM25Repository = Depends(get_text_index)
) -> RetrievalService:
    return RetrievalService(kg_repo, text_index)


def get_generation_service() -> GenerationService:
    llm_client = get_llm_client()
    return GenerationService(llm_client)


def get_chat_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    generation_service: GenerationService = Depends(get_generation_service)
) -> ChatService:
    return ChatService(retrieval_service, generation_service)
