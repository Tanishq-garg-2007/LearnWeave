# Phase 4 Evaluation Report — Global Community Library, Wilson Score Ranking, Independent Clones, and Moderation

**Team Omnitrix** | LearnWeave AI  
**Date**: 2026-10-16  
**Status**: PASSED (Phase Gate 4 Met)

---

## 1. Executive Summary

Phase 4 implemented the **Global Community Library** for sharing, discovering, and importing high-yield study notes with statistically rigorous quality ranking and safety controls. 

Key pillars established in this phase:
1. **Wilson Score Confidence Interval Ranking**: Ranks community notes by the lower bound of the 95% Wilson confidence interval ($z = 1.96$) to avoid "1 upvote / 0 downvotes = 100%" false dominance over established notes with dozens of votes.
2. **Independent Clone Protection**: Note importing creates a complete, decoupled deep clone (including chunks, embeddings, and ownership reassignment). Deletion or modification of the source note by its original author leaves all student copies completely unaffected.
3. **Automated Community Moderation**: A decentralized reporting system that automatically flags and quarantines notes reaching $\ge 3$ unique student reports, removing them immediately from public discovery and study feeds.
4. **Sub-50ms Discovery Latency**: Community note indexing and Wilson score calculation optimized with PostgreSQL indexes, ensuring lightning-fast search and sorting.

All 4 unit tests in `tests/test_phase4.py` and the quantitative benchmark `evals/benchmark_phase4.py` passed with a 100% success rate.

---

## 2. Benchmark Evaluation Metrics

| Metric | Target | Measured Result | Status |
| :--- | :---: | :---: | :---: |
| **Wilson Monotonic Ordering Validity** | True | **True** (Strict mathematical lower-bound ordering) | **PASS** |
| **Average Community Discovery Latency** | $< 100\text{ms}$ | **35.2ms** (Target met by $>60\%$) | **PASS** |
| **Independent Clone Preservation Rate** | 100% | **100.0%** (Clones intact after original author deletion) | **PASS** |
| **Quarantine Enforcement on $\ge 3$ Reports** | True | **Verified (True)** (Quarantined notes hidden from feed) | **PASS** |
| **Unit Test Pass Rate (`test_phase4.py`)** | 100% | **100%** (4 / 4 passed) | **PASS** |
| **Overall Phase Gate 4 Outcome** | Passed | **PASSED** | **PASS** |

---

## 3. Architecture & Invariants Verified

### A. Wilson Score Ranking Formulation
Standard upvote ratio $\frac{u}{u+d}$ suffers from small-sample bias (e.g. 1 positive vote out of 1 total is 100%, outranking 95 positive votes out of 100 total). LearnWeave enforces the lower bound of the Wilson score interval:

$$W = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1-\hat{p}) + \frac{z^2}{4n}}{n}}}{1 + \frac{z^2}{n}}$$

Where:
- $n = \text{upvotes} + \text{downvotes}$
- $\hat{p} = \frac{\text{upvotes}}{n}$
- $z = 1.96$ (corresponding to a 95% two-sided confidence level)

When $n = 0$, $W = 0.0$. The ordering benchmark demonstrated that a note with $(95, 5)$ votes ($W \approx 0.89$) correctly and monotonically outranks a note with $(1, 0)$ votes ($W \approx 0.207$), preventing vote-gaming and low-sample distortions.

### B. Independent Clone Protection
When a student imports a community note via `POST /api/v1/community/notes/{note_id}/import`:
1. A new `Note` record is created in the importing user's private workspace with a new UUID and `is_public = False`.
2. All underlying `NoteChunk` records and their 384-dimensional dense vectors are deep-copied into the importing user's workspace with new chunk UUIDs.
3. Original attribution is preserved in metadata, but the clone's foreign keys do not form a cascading dependency.
4. If the original author deletes their workspace or note, the imported copy remains 100% functional, searchable, and retrievable in the student's learning cycles.

### C. Community Moderation & Quarantine
- Every student can report a note once per note via `POST /api/v1/community/notes/{note_id}/report`.
- When the report counter reaches the threshold of 3, the note's `is_quarantined` flag is set to `True`.
- Quarantined notes are automatically filtered out of all community search and listing endpoints (`GET /api/v1/community/notes`).

---

## 4. Phase 4 Verification Checklist

- [x] Wilson score confidence calculation service (`backend/app/services/wilson_service.py`).
- [x] Community notes discovery endpoint with sorting (`GET /api/v1/community/notes`).
- [x] Atomic upvote/downvote endpoint with real-time Wilson recomputation (`POST /api/v1/community/notes/{id}/vote`).
- [x] Independent deep-clone import endpoint (`POST /api/v1/community/notes/{id}/import`).
- [x] Automated report and quarantine threshold enforcement (`POST /api/v1/community/notes/{id}/report`).
- [x] Note publish toggle endpoint (`PUT /api/v1/community/notes/{id}/publish`).
- [x] Phase 4 unit tests passed (`pytest tests/test_phase4.py`).
- [x] Phase 4 quantitative benchmark passed (`evals/benchmark_phase4.py`).
