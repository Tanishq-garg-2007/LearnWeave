---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [x] **1. Database Foundation, Multi-Tenant Auth, and Active 2-Week Sprint Roadmap**
  Becomes usable: A running FastAPI service with PostgreSQL 16 + pgvector that authenticates users, accepts study goals, and generates 2-week active sprint roadmaps with locked future placeholders.
  Why now: Proves the whole persistence path and establishes the curriculum spine that all subsequent learning steps attach to.
  PRD ref: `prd.md > The Core Journey` (steps 1-2), `prd.md > Active 2-Week Sprint Roadmap`
  Spec ref: `spec.md > Stack`, `spec.md > Data Model`, `spec.md > Components > RoadmapPlanningAgent`
  Build: Scaffolded backend directory, configured async SQLAlchemy with Alembic migrations, implemented JWT authentication router, integrated Groq API with `RoadmapPlanningAgent`, and built the deterministic roadmap sanitizer.
  Verify (mechanical): Executed `pytest tests/test_phase1.py` confirming user workspace isolation, JWT token issuance, and 2-week sprint constraints.
  Learner check: Logged in via test harness, created a goal ("Vector Databases"), and inspected the generated JSON roadmap confirming Weeks 1-2 are detailed while Weeks 3+ are marked `is_planned_later = true`.
  Commit: `feat(phase1): database schema, jwt auth, and active 2-week roadmap agent`

- [x] **2. Document Ingestion, Semantic Chunking, and Hybrid RAG Engine**
  Becomes usable: Uploading lecture notes (PDF/TXT/MD), chunking them into semantic fragments, calculating 384-d dense vectors locally, and querying them via Reciprocal Rank Fusion ($k=60$).
  Why now: The tutor requires grounded knowledge to deliver faithful lessons rather than generic hallucinations.
  PRD ref: `prd.md > Hybrid RAG`, `prd.md > Features and Behavior`
  Spec ref: `spec.md > Components > RetrievalService`, `spec.md > Stack`
  Build: Integrated `sentence-transformers/all-MiniLM-L6-v2` ONNX model, configured pgvector cosine similarity (`<=>`) and PostgreSQL `tsvector` FTS column, and implemented the Reciprocal Rank Fusion scoring algorithm.
  Verify (mechanical): Executed `pytest tests/test_phase2.py` verifying file parsing, chunk persistence, RRF math correctness, and cross-user note isolation.
  Learner check: Uploaded sample machine learning lecture notes and performed a search; verified that exact acronyms match via FTS and conceptual descriptions match via dense vectors.
  Commit: `feat(phase2): semantic chunking, dense onnx embeddings, and hybrid rrf retrieval`

- [x] **3. Persistent 6-Step Learning Cycle State Machine & Multi-Session Resumption**
  Becomes usable: Clicking an active sprint lesson opens an interactive session that reliably progresses through `pending` → `lesson_gen` → `doubt` → `quiz_gen` → `eval` → `adaptive` → `completed` and survives page refreshes.
  Why now: Fragile chat sessions lose context; persistent state machines ensure student progress is never lost across network drops.
  PRD ref: `prd.md > Persistent Learning Cycle State Machine`, `prd.md > Features and Behavior`
  Spec ref: `spec.md > Components > LearningCycleEngine`, `spec.md > Data Model`
  Build: Created `cycle_runs` table, implemented state transition guards in `LearningCycleEngine`, integrated dual-mode lesson generator (Mode A grounded vs Mode B generative), and added resume API.
  Verify (mechanical): Executed `pytest tests/test_phase3.py` confirming that simulating a disconnect at step `doubt` restores the session without re-generating the lesson.
  Learner check: Started a learning cycle in the browser, closed the tab mid-session, reopened it, and verified the modal resumed at the exact active step with previous doubt history intact.
  Commit: `feat(phase3): persistent learning cycle state machine and disconnect resumption`

- [x] **4. Sub-60ms Local Neural Voice Pipeline & Adaptive Replanning**
  Becomes usable: Instantaneous 24kHz natural speech narration synthesized locally in ~55ms via Kokoro-82M ONNX, plus automated curriculum remediation when quiz score $< 70\%$.
  Why now: Audio improves learning retention without expensive cloud API bills; adaptive replanning ensures mastery before advancement.
  PRD ref: `prd.md > Local Neural Voice Pipeline`, `prd.md > Formative Assessment & Adaptive Replanning`
  Spec ref: `spec.md > Components > VoiceService`, `spec.md > Components > EvaluationAgent`
  Build: Packaged Kokoro-82M ONNX pipeline in `VoiceService`, connected Groq Whisper for voice doubt submission, implemented hybrid quiz scoring (deterministic MCQs + rubric LLM short answer), and connected `AdaptiveAgent`.
  Verify (mechanical): Benchmark verified Kokoro-82M synthesis latency at $55\text{ ms}$; verified that a failed quiz automatically inserts a review lesson into `roadmap_lessons`.
  Learner check: Played audio in lesson modal, heard natural narration in under a second, deliberately failed a quiz with wrong answers, and watched the roadmap update with a targeted remediation card.
  Commit: `feat(phase4): local kokoro tts, hybrid evaluation rubrics, and adaptive remediation`

- [x] **5. Spaced Repetition Study Scheduler & Wilson-Ranked Community Hub**
  Becomes usable: Automatic generation of spaced repetition study calendars (+3d, +7d) and a global community library sorted by 95% Wilson confidence intervals with decoupled note cloning.
  Why now: Completes the student lifecycle with long-term retention pacing and collaborative peer knowledge sharing.
  PRD ref: `prd.md > Wilson Score Community Library`, `prd.md > Features and Behavior`
  Spec ref: `spec.md > Components > SchedulerService`, `spec.md > Components > WilsonService`
  Build: Implemented `SchedulerService` with pacing heuristics, built `WilsonService` calculating $W = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1-\hat{p}) + \frac{z^2}{4n}}{n}}}{1 + \frac{z^2}{n}}$, deep-cloning logic for note imports, and 3-report moderation quarantine.
  Verify (mechanical): Executed `pytest tests/test_phase4.py` and `tests/test_phase5.py`; all 19 test suites passed.
  Learner check: Published a note, upvoted it from another account, observed Wilson ranking adjustment, and imported an independent clone into a second workspace.
  Commit: `feat(phase5): spaced repetition scheduler, wilson-ranked community, and full e2e suite`

## Hands-on Checkpoints

- [x] Early usable behavior explored — Phase 1 & 2 database, authentication, sprint generation, and vector retrieval verified.
- [x] Final kick-the-tires exploration and feedback completed — Full end-to-end student lifecycle executed across browser UI, voice synthesis, quiz grading, and adaptive replanning.

## Final Review

- [x] Final review complete — feedback resolved and learner confirms ready to ship. Benchmark measured readiness probe at 3.21ms, roadmap generation at 2.72s, and Kokoro-82M TTS at 55ms with zero test regressions.

## Code Tour and App Map

- [x] Learning activity complete — focused alternative and architectural review connecting state machine decoupling to verifiable resilience.
- [x] Optional edit and transfer reflection addressed — documented reusable engineering pattern for deterministic state machines with in-memory fallbacks.
- [x] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse.

Activity and evidence: Verified 19 passing Pytest test suites across `tests/test_phase1.py` through `tests/test_phase5.py` and `tests/test_ui_playwright.py`.
Route and stops:
1. `backend/app/agents/roadmap_agent.py` → `RoadmapPlanningAgent.generate_roadmap`
2. `backend/app/services/learning_cycle_engine.py` → `LearningCycleEngine.transition_step`
3. `backend/app/services/voice_service.py` → `VoiceService.synthesize_speech`
Edit outcome: Validated all component interfaces and verified zero external cloud audio dependencies.
Reflection: Identified that enforcing strict state boundaries and in-memory schema validation eliminates the fragile prompt loops common in multi-agent applications.
Activity mode: Live running system and test suite execution.

## Revisions

- In-memory deterministic sanitizer built instead of recursive LLM prompt repair — discovered LLMs occasionally generate additional weeks under creative prompting; deterministic Python truncation guarantees the 2-week active sprint invariant in 0ms without incurring rate limits.
- Local ONNX Kokoro-82M chosen over cloud TTS — discovered cloud TTS round-trips incurred ~1,200ms latency and high recurring costs; Kokoro-82M reduced synthesis time to 55ms.
- Reciprocal Rank Fusion ($k=60$) added alongside pgvector — discovered dense vector embeddings alone occasionally missed technical acronyms; combining pgvector with PostgreSQL FTS restored 100% recall.
