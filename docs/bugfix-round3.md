# Bug-fix Round 3 (BUG-13 to BUG-22)

Scope: the next third of the audit (BUG-01 to BUG-12 were already done before this round).
Round 1 had already fixed BUG-13, 16, 17 and 22 (see `bugfix-round1.md`). Round 3 verifies those
with the round-1 regression tests and fixes BUG-14, 15, 18, 19, 20 and 21.

## Status

| Bug | Area | Status | Where |
|---|---|---|---|
| BUG-13 | Retrieval failures poison the session | Done in round 1, verified | `services/retrieval_service.py`, `tests/test_round1_fixes.py` |
| BUG-14 | Quiz output validation, duplicate quizzes, GET side effect | Done | `services/quiz_agent.py`, `api/v1/lessons.py`, `db/models.py`, migration `e4a7c1f9b203` |
| BUG-15 | Grader prompt injection, score clamp, heuristic grading, attempts | Done | `services/evaluation_agent.py`, `schemas/lessons.py` |
| BUG-16 | Cycle engine rollback and state | Done in round 1, verified | `services/cycle_engine.py` |
| BUG-17 | Global idempotency key | Done in round 1, verified | `db/models.py` (`uq_cycle_user_idempotency`) |
| BUG-18 | Duplicate revisions, title chains, version never bumped, mastery cap | Done | `services/adaptive_agent.py`, `services/learning_topics.py`, `services/evaluation_agent.py` |
| BUG-19 | Scheduler ownership, scope, status handling | Done | `services/scheduler_service.py`, `api/v1/goals.py`, `api/v1/schedule.py` |
| BUG-20 | Upload DoS, blocking the event loop | Done, with one item left (see below) | `api/v1/notes.py`, `services/document_service.py`, `services/embedding_service.py`, `api/v1/voice.py`, `services/retrieval_service.py` |
| BUG-21 | NUL bytes, binary uploads, dropped chunks, fake pages | Done | `services/document_service.py`, `api/v1/notes.py` |
| BUG-22 | Auth: 72-byte limit, email case, races | Done in round 1, verified | `services/auth_service.py`, `api/v1/auth.py` |

## Operator actions

1. **Migration.** Run `cd backend && alembic upgrade head`. The new revision `e4a7c1f9b203` depends on `7c2e9b1d4f10`.
   It merges duplicate quizzes into the earliest one (attempts are re-pointed, not deleted) and removes duplicate roadmap version rows. Then it adds `uq_assessment_lesson` and `uq_roadmap_version_number`.
2. **Migration history mismatch.** In the local environment checked for this round, every database was stamped with `a3f5c7d9e1b2`, which is not in this repo's chain (`1adf92ff4c6e` -> `7c2e9b1d4f10` -> `e4a7c1f9b203`). Those databases already had `uq_roadmap_version_number` and the round-1 constraints. Reconcile the stamp before running `alembic upgrade head` there. A fresh database built from this repo's migrations upgrades cleanly and `alembic check` reports no drift.

## Behaviour changes that clients will notice

| Route | Before | After |
|---|---|---|
| `GET /lessons/{id}/quiz` | Generated the quiz if missing (LLM call on GET) | Read-only. 404 `Quiz has not been generated yet` if none exists. Never calls the LLM. |
| `POST /lessons/{id}/quiz` | Did not exist (405 from the frontend) | Generates the quiz if missing, otherwise returns it. Idempotent. |
| Quiz output that fails validation | Missing options filled with placeholders, `correct_answer` defaulted to `A` | 503 with `Retry-After: 30` and a `reference`. Nothing is stored. |
| Stored quiz that fails validation | 500 on every request | GET: 409. POST: regenerated in place if no attempts exist, otherwise 409. |
| `POST /lessons/{id}/quiz/submit` body | `{answers}` | `{answers, assessment_id?}`. A mismatched `assessment_id` returns 409. |
| `written_answer` | Unbounded | At most 2000 characters (422 above that). `answers` at most 10 items. |
| Grader unavailable or returns an invalid score | Heuristic word-overlap score, recorded as a normal attempt | 503 with `Retry-After`. Nothing is recorded. Scores outside [0, 1] or non-numeric are rejected, never clamped. |
| Attempts per quiz | Unlimited | 3 per student per quiz. The 4th returns 429. |
| Failed attempt | Adaptive replanning ran only through the cycle engine | Replanning runs on submit. The result is in `adaptation` (`remedial_inserted`, `remedial_exists`, or `unavailable`). |
| Remedial revision | A new `Targeted Revision: X` on every failure, chained titles on repeats | One open revision per topic, reused on repeat failures. The title is always `Targeted Revision: <original title>`. |
| Roadmap version | Never changed on `roadmaps.version` | `roadmaps.version` is bumped with each new `roadmap_versions` row. |
| Remedial lesson status and session | `not_started`, `scheduled` at now+1 day | `pending`, `pending` at 18:00 UTC tomorrow (the same slot as the scheduler). |
| First attempt mastery | Capped at 0.7 (blended with a default 0.0) | Equal to the attempt's score. Later attempts blend 0.3 prior and 0.7 new. |
| `AnswerEvaluation` | No grading source | Adds `graded_by` (`deterministic` or `llm`). Additive. |
| `/voice/speak` | Synthesis blocked the event loop | Runs in a worker thread. |
| `/voice/listen`, `/notes/upload` | Whole body read before the size check | Streamed in 1 MiB chunks. 413 once the 25 MiB limit is passed. |
| `/notes/search` `top_k` | Unbounded | `1 <= top_k <= 20` (422 otherwise). |
| `/notes/upload` file types | Any file decoded as text | Detected from magic bytes. PDF, or valid UTF-8 text with no NUL and few control bytes. Anything else is 415. |

## Deliberate deviations

- **BUG-18, topic keys.** The audit asked for mastery and weak areas to be keyed by lesson id. They stay keyed by lesson title. The frontend (`LearnerProfile.weak_areas`, `topic_mastery`) and the scheduler read them as display strings, and a key migration would need a data migration. The fix that matters is in `services/learning_topics.py`: a remedial revision is mapped to the lesson it revises, so passing the revision clears the original topic's weak area.
- **BUG-19, weak-topic matching.** `weak_areas` stores titles verbatim, so matching is exact. LIKE escaping no longer applies.
- **BUG-14, quiz fallback on LLM transport failure.** A transport error still uses the deterministic fallback quiz, as before. Only invalid model output is rejected. The audit's BUG-06 ("do not persist the fallback") is not changed by this round.

## Not done in this round

- **BUG-20, background processing.** Ingest still runs inside the upload request. Large uploads hold the connection until they finish.
- **BUG-20, proxy body limit.** Starlette parses the whole multipart body to disk before the handler runs, so the 413 check bounds memory, not disk. A body-size limit at the proxy or in `main.py` is still needed.
- **BUG-18, frontend.** The `LearningCycleModal` text "Adaptive replanning has been triggered" should read `adaptation.action` from the submit response rather than always showing it.
- **BUG-25 (status transitions).** `lesson_agent.py` still checks `not_started`. `PUT /schedule/{id}/status` does not sync the lesson status.

## Tests

- `tests/test_round1_fixes.py`: 17 passed (round-1 regressions, including BUG-13, 16, 17, 22).
- `tests/test_round3_ingest.py`: 13 passed (BUG-20, BUG-21).
- `tests/test_round3_scheduler.py`: 8 passed (BUG-19).
- `tests/test_round3_quiz.py`: 18 passed (BUG-14, 15, 18).
- Total: 56 passed, with the LLM stubbed.
- `tests/test_phase2.py` and `tests/test_phase3.py` were updated for the contract (quiz generation is POST, new sessions are `pending`). They call Groq and were not run here (network is blocked in this sandbox). The full `tests/` folder hangs without network access, so run the round files on their own unless Groq is reachable.
