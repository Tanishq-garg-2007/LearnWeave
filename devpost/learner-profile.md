---
doc: learner-profile
---

# Learner Profile

## Initial Idea
Build **LearnWeave AI**, a privacy-preserving, cost-controlled, and agentic personalized learning platform. Unlike generic LLM chat windows that suffer from context drift and unbounded prompt costs, LearnWeave structures learning into an active 2-week sprint roadmap, a resilient 6-step persistent learning cycle, local neural TTS for vocal accessibility, hybrid RAG over user notes, and adaptive remediation when test scores drop.

## Demonstrated Technical and Agent Experience
- **Technical Background**: Proficient in Python (FastAPI, SQLAlchemy, Pytest), Modern JavaScript/TypeScript (React 18, Vite, Tailwind CSS), and Relational Databases (PostgreSQL 16 with pgvector and full-text search).
- **Agent Workflow Experience**: Experienced with plan-first and spec-driven agent workflows. Prefers explicit state machine definitions, deterministic fallback sanitizers, and isolated micro-services over unconstrained, unpredictable multi-agent swarms.
- **Tools in Use**: Visual Studio Code, Antigravity IDE, Docker Compose, Groq Cloud API, ONNX Runtime (Kokoro-82M TTS and all-MiniLM-L6-v2 embeddings).

## Planning-Workflow Experience
Familiar with spec-driven development. Believes that engineering rigor (schema validation, automated invariant testing, recovery across network drops) should precede code writing to avoid expensive debugging loops.

## Desired Learning Outcome
Master the orchestration of deterministic agentic systems combined with low-latency local inference (sub-100ms local ONNX neural TTS and dense embeddings), alongside hybrid Reciprocal Rank Fusion ($k=60$) search, validating that high-performance AI apps can run economically without cloud vendor lock-in.

## Learning Moments
- **Deterministic Roadmap Sanitizer**: Rather than triggering recursive and costly LLM repair prompts when roadmap JSON output deviates from constraints, built an in-memory sanitizer enforcing the 2-week active sprint window and future placeholders.
- **State Machine Resilience**: Implemented persistent step transitions in `cycle_runs` so that student sessions resume flawlessly from the exact step (`pending` → `lesson_gen` → `doubt` → `quiz_gen` → `eval` → `adaptive` → `completed`) even after client disconnection.
- **Local Neural Voice Latency**: Configured Kokoro-82M ONNX locally to achieve ~55ms audio synthesis for 24kHz WAV, eliminating cloud audio API costs and latency.

## Interests, Inspirations, and Goals
- **Inspirations**: Khan Academy's structured pedagogy combined with modern agentic workflows (like AutoGPT/Manus concepts restrained to rigorous state machines).
- **Goals**: Create an open-source, reproducible proof-of-concept for the Devpost Build With AI: Basics hackathon that demonstrates end-to-end pedagogical value for technical students.

## Vocabulary and Concepts Likely to Need Explanation
- **Well Understood**: FastAPI dependency injection, PostgreSQL pgvector cosine similarity, Docker orchestration, JWT authentication, TanStack Query cache invalidation.
- **Clarified During Planning**: Reciprocal Rank Fusion ($RRF$) mathematical scoring mechanics, Wilson score lower bound confidence intervals for community content sorting, and ONNX runtime threading models.

## Collaboration and Communication Preferences
- Direct, concise, and technically grounded.
- Prefers code backed by automated unit, integration, and E2E Playwright tests.

## Areas Where the Learner Wants Ownership
- Architecture design, database schema invariants, pedagogical constraints (e.g. 2-week sprint cap), and evaluation criteria rubrics.

## Review Format
markdown

## Notes and Open Questions
- System benchmark results and end-to-end verification are completed with 19/19 passing tests in Pytest.
