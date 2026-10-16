# Technical Decisions & Architecture Log
## LearnWeave AI — Team Omnitrix

### 1. External LLM & Transcription Provider: Groq
- **Provider**: Groq Cloud API
- **Official Documentation**: https://console.groq.com/docs, https://console.groq.com/docs/models, https://console.groq.com/docs/rate-limits
- **Primary LLM**: `qwen/qwen3.8-27b`
  - Context Window: 131,072 tokens
  - Max Completion Tokens: 16,384 tokens
  - Features: Tools, JSON mode, Reasoning controls (`reasoning_format: "hidden"` / `"parsed"`)
  - Free-tier rate limits: 30 requests/min, 1,000 req/day, 8,000 tokens/min, 200,000 tokens/day
  - Cost: $0.0000008 prompt, $0.000004 completion per token (evaluated under free-tier quota)
- **Fallback LLM**: `openai/gpt-oss-20b`
  - Context Window: 131,072 tokens
  - Max Completion Tokens: 65,536 tokens
  - Features: Tools, JSON mode, Structured Outputs, Reasoning
  - Free-tier rate limits: 30 requests/min, 1,000 req/day, 8,000 tokens/min, 200,000 tokens/day
- **Speech-to-Text**: `whisper-large-v3-turbo`
  - Audio formats: WAV, MP3, M4A, WEBM, FLAC
  - Context Window: 448 tokens
  - Limits: 20 requests/min, 2,000 req/day, 7,200 audio seconds/hour, 28,800 audio seconds/day
- **Centralized Provider Pattern**:
  - Central `GroqClient` wrapping HTTP requests with exponential backoff + jitter, `Retry-After` header handling, rolling token accounting, and fallback invocation.
  - Default per-call ceiling: 6,000 combined input + output tokens.
  - Reason: Directly calling Groq across scattered routes leads to rate-limit stampedes and budget exhaustion.

### 2. Database & Search: PostgreSQL + pgvector
- **Engine**: PostgreSQL 16 with pgvector extension (`pgvector/pgvector:pg16` image)
- **Documentation**: https://github.com/pgvector/pgvector, https://www.postgresql.org/docs/16/textsearch.html
- **Vector Indexing**: HNSW index with cosine distance (`vector_cosine_ops`)
- **Full-Text Indexing**: PostgreSQL native `tsvector` with `to_tsvector('english', ...)` and GIN indexing
- **Hybrid Fusion**: Reciprocal Rank Fusion (RRF) with constant k=60 combining vector ranking + FTS ranking in application/SQL logic.
- **Data Integrity**: Foreign keys with cascade deletion, unique constraints on `(user_id, note_id)` for votes, and strict owner filtering at database layer.

### 3. Local Embedding Model
- **Model**: `all-MiniLM-L6-v2` (dimension: 384)
- **Documentation**: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- **Runtime**: Local fast ONNX or PyTorch sentence-embedding inference without calling external APIs, ensuring zero Groq token consumption for RAG embeddings.
- **License**: Apache 2.0

### 4. Text-to-Speech: Kokoro-82M
- **Engine**: Kokoro-82M (v1.0) running locally (ONNX/PyTorch engine)
- **Documentation**: https://huggingface.co/hexgrad/Kokoro-82M, https://github.com/hexgrad/kokoro
- **Audio Output**: 24,000Hz mono WAV
- **License**: Apache 2.0
- **Fallback**: Clean deterministic WAV synthesis fallback when local weights are loading or on resource-constrained test environments.

### 5. Backend Framework
- **Framework**: FastAPI with Pydantic v2 & SQLAlchemy 2.0 (asyncpg / psycopg)
- **Documentation**: https://fastapi.tiangolo.com, https://docs.pydantic.dev/2.0/, https://docs.sqlalchemy.org/en/20/
- **Design Rule (Ponytail Skill)**:
  - Standard library and native platform features first.
  - Unified clean modular monolithic backend in `backend/app`.
  - No unnecessary microservices.
  - Strict Pydantic models for request/response and LLM JSON output schemas.

### 6. Frontend Stack
- **Framework**: React 18 / Vite / TypeScript / Tailwind CSS
- **State & Server Data**: TanStack Query v5
- **Testing**: Vitest + Testing Library + Playwright E2E
