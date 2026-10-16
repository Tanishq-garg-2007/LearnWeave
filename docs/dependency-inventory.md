# External Dependency Inventory
## LearnWeave AI — Approved Dependencies

| Package | Version | Purpose | Documentation URL | License | Justification |
|---------|---------|---------|-------------------|---------|---------------|
| `fastapi` | >=0.115.0 | Async web API framework | https://fastapi.tiangolo.com | MIT | Standard performant ASGI framework with OpenAPI generation |
| `uvicorn[standard]` | >=0.30.0 | ASGI web server | https://www.uvicorn.org | BSD-3-Clause | Production-ready ASGI server for FastAPI |
| `pydantic` | >=2.9.0 | Data validation & LLM structured schema parsing | https://docs.pydantic.dev | MIT | Pydantic v2 high-speed Rust-core validation |
| `pydantic-settings` | >=2.4.0 | Environment configuration management | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | MIT | Type-safe environment variable parsing |
| `sqlalchemy` | >=2.0.35 | Database ORM & SQL query builder | https://docs.sqlalchemy.org | MIT | Industry standard database abstraction with pgvector support |
| `alembic` | >=1.13.0 | Database migration engine | https://alembic.sqlalchemy.org | MIT | Version-controlled schema migrations |
| `psycopg[binary]` / `asyncpg` | >=3.2.0 | PostgreSQL database driver | https://www.psycopg.org/psycopg3/docs/ | LGPL-3.0 | Official modern PostgreSQL client supporting pgvector |
| `pgvector` | >=0.3.0 | pgvector Python integration for SQLAlchemy | https://github.com/pgvector/pgvector-python | Apache-2.0 | Official vector extension types for SQLAlchemy |
| `httpx` | >=0.27.0 | Centralized async HTTP client for Groq | https://www.python-httpx.org | BSD-3-Clause | Standard async HTTP client with connection pooling, retries, and timeout control |
| `pytest` | >=8.3.0 | Automated testing framework | https://docs.pytest.org | MIT | Primary test runner for unit, integration, and workflow tests |
| `pytest-asyncio` | >=0.24.0 | Async test support for pytest | https://github.com/pytest-dev/pytest-asyncio | Apache-2.0 | Async test execution for FastAPI/SQLAlchemy endpoints |
| `pypdf` | >=4.3.0 | Local PDF text extraction | https://pypdf.readthedocs.io | BSD-3-Clause | Lightweight, pure-Python PDF reader without heavy C/C++ dependencies |
| `python-multipart` | >=0.0.9 | Multipart form parser for file uploads | https://github.com/andrew-d/python-multipart | Apache-2.0 | Required by FastAPI for document and audio file uploads |
| `onnxruntime` / `fastembed` | >=1.19.0 | Local embedding inference | https://onnxruntime.ai | MIT | Lightweight local inference for all-MiniLM-L6-v2 without huge torch installs |
| `kokoro-onnx` | >=0.3.0 | Local lightweight Kokoro-82M TTS | https://github.com/thewh1teagle/kokoro-onnx | MIT | Lightweight ONNX inference for Kokoro-82M TTS |
| `soundfile` / `numpy` | >=0.12.0 | Audio processing and WAV writing | https://pysoundfile.readthedocs.io | BSD-3-Clause | Audio I/O for synthesized speech validation |
| `react` | ^18.3.1 | Frontend UI framework | https://react.dev | MIT | Primary user interface |
| `vite` | ^5.4.0 | Frontend build tool | https://vitejs.dev | MIT | Rapid HMR and optimized bundler |
| `@tanstack/react-query` | ^5.56.0 | Server-state management & caching | https://tanstack.com/query | MIT | Robust API synchronization, retries, and optimistic UI |
| `tailwindcss` | ^3.4.0 | Styling framework | https://tailwindcss.com | MIT | Responsive, clean styling |
| `lucide-react` | ^0.440.0 | Iconography | https://lucide.dev | ISC | Crisp UI icons |
| `vitest` | ^2.1.0 | Frontend unit testing | https://vitest.dev | MIT | Vite-native unit testing |
| `@playwright/test` | ^1.47.0 | End-to-end integration test runner | https://playwright.dev | Apache-2.0 | Multi-browser E2E testing for full learner journey |
