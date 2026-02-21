# Production-ready RAG Knowledge Graph System

A comprehensive **Hybrid Extraction + GraphRAG/TextRAG** system built with FastAPI, Neo4j, and PostgreSQL. This production-minded architecture features:

- **Hybrid Extraction**: REBEL (supervised) + LLM (zero-shot) with entity canonicalization
- **Dual Retrieval**: GraphRAG with automatic fallback to TextRAG (BM25)
- **Provenance Tracking**: Full citation tracking from documents to graph edges
- **Job Queue System**: Celery-based asynchronous ingestion pipeline
- **Multi-tenant Ready**: User/tenant isolation throughout
- **Observability**: Structured logging, correlation IDs, progress tracking
- **Idempotent Operations**: Safe retries and reprocessing

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  API Layer: /documents, /ingestion, /chat, /kg             │
├─────────────────────────────────────────────────────────────┤
│  Services: Document, Ingestion, Extraction,                 │
│            Canonicalization, KG, Retrieval, Generation       │
├─────────────────────────────────────────────────────────────┤
│  Domain: Models, Ports (Interfaces)                         │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure:                                             │
│    - PostgreSQL (Documents, Chunks, Jobs)                   │
│    - Neo4j (Knowledge Graph with Provenance)                │
│    - BM25 Index (Text Search)                               │
│    - Celery + Redis (Job Queue)                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (OpenAI API key, etc.)
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL, Neo4j, Redis
docker compose up -d

# Verify services are running
docker ps
```

### 3. Run Application

```bash
# Start FastAPI server
python -m uvicorn app.main:app --reload

# In another terminal, start Celery worker
celery -A app.infra.queue.celery_app worker --loglevel=info

# Optional: Start Flower (Celery monitoring)
celery -A app.infra.queue.celery_app flower
```

## API Usage

### Upload Document

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@document.pdf"
```

Response:

```json
{
  "doc_id": "doc_abc123",
  "filename": "document.pdf",
  "size_bytes": 1234567,
  "created_at": "2026-02-16T10:30:00Z"
}
```

### Start Ingestion

```bash
curl -X POST "http://localhost:8000/ingestion/jobs" \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "doc_abc123"}'
```

Response:

```json
{
  "job_id": "job_xyz789",
  "task_id": "celery-task-id",
  "status": "submitted",
  "message": "Ingestion job submitted to queue"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/ingestion/jobs/job_xyz789"
```

Response:

```json
{
  "id": "job_xyz789",
  "doc_id": "doc_abc123",
  "status": "done",
  "current_step": "build_text_index",
  "progress": {
    "extract_text": { "status": "done", "stats": { "pages": 10 } },
    "chunk": { "status": "done", "stats": { "chunks": 45 } },
    "canonicalize": {
      "status": "done",
      "stats": { "entities": 23, "relations": 67 }
    },
    "upsert_graph": {
      "status": "done",
      "stats": { "entities": 23, "relations": 67 }
    }
  },
  "created_at": "2026-02-16T10:31:00Z",
  "completed_at": "2026-02-16T10:35:00Z"
}
```

### Ask Question (Chat)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why is backpropagation related to calculus?",
    "mode": "auto"
  }'
```

Response:

```json
{
  "answer": "Backpropagation is related to calculus because...\n\n**Sources:**\n[1] Document doc_abc123, Page 5-6\n[2] Document doc_abc123, Page 8",
  "mode_used": "graph",
  "confidence": 0.85,
  "evidence": [
    {
      "doc_id": "doc_abc123",
      "chunk_id": "chunk_def456",
      "page_start": 5,
      "page_end": 6,
      "snippet": "Backpropagation uses the chain rule...",
      "score": 0.92,
      "source_type": "graph"
    }
  ]
}
```

### Search Knowledge Graph

```bash
curl -X POST "http://localhost:8000/kg/entities/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "neural network", "limit": 10}'
```

## Ingestion Pipeline

The system processes documents through these steps:

1. **EXTRACT_TEXT**: PDF → Text with page tracking
2. **CHUNK**: Text → Chunks (512 tokens, 50 overlap)
3. **EXTRACT_TRIPLES_REBEL**: Supervised extraction
4. **EXTRACT_TRIPLES_LLM**: Zero-shot extraction
5. **UNION_POOL**: Combine triples with deduplication
6. **CANONICALIZE**: Entity resolution via clustering
7. **UPSERT_GRAPH**: Neo4j knowledge graph upsert
8. **BUILD_TEXT_INDEX**: BM25 index for text search

All steps are:

- **Idempotent**: Safe to rerun
- **Retryable**: Automatic retries with backoff
- **Observable**: Progress tracking and logging

## Retrieval Modes

### Auto Mode (Recommended)

Intelligent routing:

- Tries GraphRAG first
- Falls back to TextRAG if graph confidence < threshold
- Best for most use cases

### Graph Mode

GraphRAG only:

- Entity resolution from question
- K-hop graph traversal
- Path scoring with provenance
- Best for structured knowledge queries

### Text Mode

TextRAG (BM25) only:

- Direct text similarity search
- Fast and reliable
- Best for keyword/phrase matching

### Hybrid Mode

Combines both:

- Graph + Text evidence
- Interleaved results
- Best for comprehensive coverage

## Configuration

Key settings in `.env`:

```env
# LLM Provider
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

# Processing
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Retrieval
GRAPH_CONFIDENCE_THRESHOLD=0.7
TOP_K_RETRIEVAL=10
GRAPH_HOP_LIMIT=3

# Canonicalization
ENTITY_SIMILARITY_THRESHOLD=0.85
```

## Project Structure

```
app/
├── main.py                  # FastAPI application
├── core/                    # Core infrastructure
│   ├── config.py           # Settings
│   ├── logging.py          # Structured logging
│   ├── exceptions.py       # Custom exceptions
│   ├── middleware.py       # Request middleware
│   └── auth.py             # Authentication
├── domain/                  # Domain layer
│   ├── models.py           # Business entities
│   └── ports.py            # Repository interfaces
├── services/                # Business logic
│   ├── document_service.py
│   ├── ingestion_service.py
│   ├── extraction_service.py
│   ├── canonicalization_service.py
│   ├── kg_service.py
│   ├── retrieval_service.py
│   ├── generation_service.py
│   └── chat_service.py
├── pipelines/               # Orchestration
│   └── ingest_pipeline.py
├── infra/                   # Infrastructure
│   ├── postgres/           # PostgreSQL
│   ├── neo4j/              # Neo4j
│   ├── index/              # BM25
│   └── queue/              # Celery
├── llm/                     # LLM clients
│   ├── client.py
│   └── prompts.py
├── utils/                   # Utilities
│   ├── pdf.py
│   ├── chunking.py
│   └── text.py
├── api/                     # API layer
│   ├── routers/
│   │   ├── documents.py
│   │   ├── ingestion.py
│   │   ├── kg.py
│   │   ├── chat.py
│   │   └── health.py
│   └── deps.py             # Dependency injection
└── schemas/                 # API schemas
    ├── documents.py
    ├── ingestion.py
    ├── kg.py
    └── chat.py
```

## Production Considerations

### Security

- JWT-based authentication (ready to enable)
- Tenant isolation at DB/Graph level
- Input validation on all endpoints
- Rate limiting (TODO: add middleware)

### Scalability

- Stateless API servers (horizontal scaling)
- Async job processing with Celery
- Neo4j connection pooling
- BM25 index can be moved to Redis for distributed access

### Observability

- Structured JSON logs
- Correlation IDs for request tracing
- Job progress tracking
- Health/readiness endpoints

### Reliability

- Idempotent operations
- Automatic retries with exponential backoff
- Graceful error handling
- Database transaction management

## Development

```bash
# Run tests (TODO: add test suite)
pytest

# Format code
black app/
isort app/

# Type checking
mypy app/

# Linting
flake8 app/
```

## Monitoring

- **API Logs**: Structured JSON in stdout
- **Celery**: Monitor with Flower at `http://localhost:5555`
- **Neo4j**: Browse at `http://localhost:7474`
- **Metrics**: `/health` and `/health/ready` endpoints

## License

MIT License

## Contributors

Built with production-ready patterns for RAG systems with knowledge graphs.
