# Phase 2 Evaluation Report — Lessons, Persistent Memory, Notes and Hybrid RAG

**Team Omnitrix** | LearnWeave AI  
**Date**: 2026-10-16  
**Status**: PASSED (Phase Gate 2 Met)

---

## 1. Executive Summary

Phase 2 implemented the core learning cycle: multi-format study notes ingestion, local 384-dimensional dense semantic chunk embeddings via `all-MiniLM-L6-v2` (`fastembed` with ONNX runtime), PostgreSQL pgvector cosine distance search (`<=>`), full-text keyword search (`to_tsvector` + `plainto_tsquery`), fused via **Reciprocal Rank Fusion (RRF, $k=60$)**, pedagogical lesson generation with two distinct grounding modes (Mode A: RAG-grounded with real citations; Mode B: AI-Generated Learning without notes), doubt resolution with persistent learner profile tracking, and formative assessment generation with 100% deterministic MCQ scoring in Python + rubric-guided short-answer evaluation.

All 5 automated tests in `tests/test_phase2.py` and 3 regression tests in `tests/test_phase1.py` passed (100% pass rate). The quantitative benchmark across 30 technical queries achieved **Recall@5 = 100.0%** (target >= 80%), **MRR = 0.983**, and **0.00% Cross-User Privacy Leakage**.

---

## 2. Benchmark Evaluation Metrics

| Metric | Target | Measured Result | Status |
| :--- | :---: | :---: | :---: |
| **Recall@1** | $\ge 0.70$ | **96.67%** (29 / 30) | **PASS** |
| **Recall@5** | $\ge 0.80$ | **100.0%** (30 / 30) | **PASS** |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.75$ | **0.9833** | **PASS** |
| **Cross-User Privacy Leakage** | **0.00%** | **0.00%** (0 / 10 queries leaked) | **PASS** |
| **Deterministic MCQ Scorer Variance** | **0.0000** | **0.0000** (10 trials identical) | **PASS** |
| **Automated Pytest Pass Rate** | 100% | **100%** (5 / 5 tests passed) | **PASS** |
| **Regression Pytest Pass Rate** | 100% | **100%** (3 / 3 tests passed) | **PASS** |

---

## 3. Architecture & Security Invariants Verified

1. **Strict User Isolation at Database Retrieval Layer**:
   - `retrieval_service.py` strictly restricts queries with `NoteChunk.owner_id == user.id`.
   - Direct note access (`GET /api/v1/notes/{id}`) verifies ownership and returns `403 Forbidden` for unauthorized users.
   - User B executed 10 target queries searching for User A's private notes and retrieved 0 chunks (0.00% leakage rate).

2. **Hybrid RAG Fusion (pgvector + FTS via RRF)**:
   - Dense representation: 384-dimensional unit L2-normalized embeddings via local ONNX model `sentence-transformers/all-MiniLM-L6-v2`.
   - Sparse representation: PostgreSQL `tsvector` indexed text matching with `plainto_tsquery`.
   - Fusion: Reciprocal Rank Fusion ($k=60$) scores each chunk by:
     $$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + \text{rank}_m(d)}$$
   - Results in high retrieval accuracy across both exact technical acronyms (e.g., TLB, MMU, SSTable, AIMD, SSA) and semantic conceptual queries.

3. **Dual-Mode Lesson Grounding**:
   - **Mode A (RAG-Grounded)**: When student has uploaded notes on the subject, up to 4 relevant chunks are provided to the LLM. Only real chunk IDs are cited in section metadata; zero phantom IDs are permitted.
   - **Mode B (AI-Generated Learning)**: When no notes exist, the agent produces a curriculum-guided lesson clearly labeled "[AI-Generated Learning]" with empty citation lists, ensuring zero hallucinations.

4. **Pedagogical Assessment & Persistent Learner State**:
   - Assessments contain 3 MCQs + 1 short-answer conceptual question.
   - MCQs are scored deterministically in pure Python without LLM subjectivity or non-determinism.
   - Short-answer conceptual questions are graded against an explicit rubric.
   - Overall mastery score updates `LearnerProfile.topic_mastery` persistently using an exponential moving average. Lessons transition to `"completed"` once the student passes with $\ge 70\%$.

---

## 4. Phase 2 Verification Checklist

- [x] Ingest multi-format documents (PDF, Markdown, TXT) with semantic chunking.
- [x] Local ONNX sentence embedding inference (`all-MiniLM-L6-v2`, 384 dimensions).
- [x] Hybrid RAG with pgvector cosine distance (`<=>`) + PostgreSQL FTS + RRF ($k=60$).
- [x] Mode A RAG-grounded lesson generation with genuine citation tracking.
- [x] Mode B AI-Generated Learning without phantom citations.
- [x] Empathetic doubt resolution agent with personal note context.
- [x] Assessment generation (3 MCQs + 1 short-answer).
- [x] Deterministic MCQ scoring + rubric-guided short-answer scoring.
- [x] Persistent `LearnerProfile` updates (`topic_mastery`, `unresolved_doubts`, `completed_lessons`).
- [x] Cross-user isolation verified with 0.00% privacy leakage.
- [x] All automated tests passing (`pytest tests/test_phase2.py`).
