# Quick Start Guide

## Complete Setup (5 minutes)

### 1. Prerequisites
- Python 3.10+
- Docker Desktop
- OpenAI API key (or Azure OpenAI)

### 2. Installation

```powershell
# Clone/navigate to project
cd RAG

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup directories
.\setup.ps1
```

### 3. Configuration

Edit `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 4. Start Services

```powershell
# Terminal 1: Start infrastructure
docker compose up -d

# Terminal 2: Start FastAPI
python -m uvicorn app.main:app --reload

# Terminal 3: Start Celery worker
celery -A app.infra.queue.celery_app worker --loglevel=info
```

### 5. Verify

Open http://localhost:8000/docs - You should see the API documentation.

## First Document Processing

### Using API (curl)

```bash
# 1. Upload PDF
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@your_document.pdf"

# Response will contain: doc_id

# 2. Start ingestion
curl -X POST "http://localhost:8000/ingestion/jobs" \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "doc_abc123"}'

# Response will contain: job_id

# 3. Check status
curl "http://localhost:8000/ingestion/jobs/job_xyz789"

# 4. Query when complete
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "mode": "auto"
  }'
```

### Using Python Script

```python
python example_usage.py
```

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                  Client Request                      │
└──────────────────┬──────────────────────────────────┘
                   │
         ┌─────────▼────────┐
         │   FastAPI App    │
         │  (main.py)       │
         └─────────┬────────┘
                   │
         ┌─────────▼────────┐
         │   API Routers    │
         │ /documents       │
         │ /ingestion       │
         │ /chat            │
         │ /kg              │
         └─────────┬────────┘
                   │
         ┌─────────▼────────┐
         │    Services      │
         │ DocumentService  │
         │ IngestionService │
         │ ChatService      │
         │ RetrievalService │
         │ GenerationService│
         └─────────┬────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐
│PostgreSQL│ │  Neo4j   │ │  Redis   │
│ Docs     │ │Knowledge │ │  Queue   │
│ Chunks   │ │  Graph   │ │  Cache   │
│ Jobs     │ │Provenance│ │          │
└──────────┘ └──────────┘ └──────────┘
                   │
         ┌─────────▼────────┐
         │  Celery Worker   │
         │  (Background)    │
         │  - Extraction    │
         │  - Canonicalize  │
         │  - Build Graph   │
         └──────────────────┘
```

## Key Features

### 🔄 Hybrid Extraction
- **REBEL**: Supervised model (reliable, structured)
- **LLM**: Zero-shot extraction (comprehensive)
- **Union Pool**: Combines both with deduplication

### 🧠 Dual Retrieval
- **GraphRAG**: Entity resolution → Graph traversal → Path scoring
- **TextRAG**: BM25 full-text search
- **Auto Router**: Intelligent fallback based on confidence

### 📍 Provenance Tracking
Every triple/relation includes:
- Source document ID
- Source chunk ID
- Page range
- Confidence score
- Extraction method

### ⚙️ Async Processing
- Upload → Immediate response
- Processing → Background queue
- Progress → Real-time tracking
- Idempotent → Safe retries

### 🎯 Production Ready
- **Bounded Contexts**: Clear domain separation
- **Dependency Injection**: Testable, swappable
- **Structured Logging**: JSON logs with correlation IDs
- **Multi-tenant**: User/tenant isolation
- **Error Handling**: Custom exceptions with clear boundaries

## Monitoring

### Health Checks
```bash
# Basic health
curl http://localhost:8000/health

# Readiness (includes dependencies)
curl http://localhost:8000/health/ready
```

### Celery Monitoring
```bash
# Start Flower
celery -A app.infra.queue.celery_app flower

# Open http://localhost:5555
```

### Neo4j Browser
Open http://localhost:7474
- Username: neo4j
- Password: 12345678

Query examples:
```cypher
// Count entities
MATCH (e:Entity {tenant_id: 'dev_tenant'})
RETURN count(e)

// Show entity with relations
MATCH (e:Entity {canonical_name: 'neural network'})-[r]->(t)
RETURN e, r, t LIMIT 10
```

### PostgreSQL
```bash
docker exec -it rag_postgres psql -U rag_user -d rag_db

# SQL queries
\dt  -- List tables
SELECT * FROM documents;
SELECT * FROM ingestion_jobs;
```

## Troubleshooting

### Celery worker not processing jobs
```bash
# Check Redis
docker exec -it rag_redis redis-cli ping

# Check Celery logs
celery -A app.infra.queue.celery_app worker --loglevel=debug
```

### LLM extraction failing
- Check OPENAI_API_KEY in .env
- Check API quota/limits
- Verify model name (gpt-4o-mini recommended)

### Neo4j connection error
```bash
# Check Neo4j is running
docker logs rag_neo4j

# Test connection
docker exec -it rag_neo4j cypher-shell -u neo4j -p 12345678
```

### Database migration
```bash
# Initialize Alembic (first time)
alembic init app/infra/postgres/migrations

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

## Configuration Options

See `.env` for all configuration options. Key settings:

```env
# Processing
CHUNK_SIZE=512                  # Token size per chunk
CHUNK_OVERLAP=50                # Overlap between chunks
MAX_CONCURRENT_JOBS=2           # Parallel ingestion jobs

# Retrieval
GRAPH_CONFIDENCE_THRESHOLD=0.7  # When to use graph vs text
TOP_K_RETRIEVAL=10              # Evidence pieces to retrieve
GRAPH_HOP_LIMIT=3               # Max graph traversal depth

# Canonicalization
ENTITY_SIMILARITY_THRESHOLD=0.85  # Entity clustering threshold
```

## Next Steps

1. **Add Authentication**: Enable JWT tokens in production
2. **Add Tests**: Create test suite with pytest
3. **Add Observability**: Integrate OpenTelemetry
4. **Scale**: Deploy to Kubernetes with horizontal scaling
5. **Enhance Extraction**: Fine-tune REBEL or add custom NER
6. **Add More LLM Providers**: Anthropic, local models

## License

MIT License - Production-ready RAG system with knowledge graphs
