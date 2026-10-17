# Bug-fix Round 4 (BUG-23 to BUG-29, plus frontend contract)

Base: `LearnWeave-round1` with the "round 3" overlay (which was BUG-13 to 22, i.e. round 2) merged in.

## Finding: frontend contract bugs were never fixed in the supplied trees
`frontend/src` was byte-identical in `LearnWeave-main` and `LearnWeave-round1`, and still had the broken
contract from BUG-03/04/05/09/11 (wrong paths, field names, status vocab). Fixed here in `api/client.ts`
through normalizers, so components only needed small edits.

## Status
| Bug | Status | Where |
|---|---|---|
| BUG-23 Groq client | Done, one item open | `services/groq_client.py`, `config.py`, `main.py` |
| BUG-24 Roadmap agent | Done | `services/roadmap_agent.py`, `api/v1/goals.py` |
| BUG-25 Status vocabulary | Done | `services/lesson_status.py`, `api/v1/roadmaps.py`, `services/scheduler_service.py`, `services/lesson_agent.py` |
| BUG-26 Error leakage | Done in round 1; re-checked (remaining `str(exc)` are our own NotFound/Step messages) | - |
| BUG-27 Rate limits | Done (in-process) | `api/rate_limit.py` + route dependencies |
| BUG-28 Input bounds | Done | schemas, `api/sql_utils.py` (LIKE escaping) |
| BUG-29 Frontend errors/session | Done, JWT storage open | `api/client.ts`, `App.tsx`, `components/ErrorBoundary.tsx` |
| BUG-03/04/05/09/11 (frontend side) | Done | `api/client.ts`, `LearningCycleModal`, `NotesView`, `ScheduleView`, `CommunityView` |

## What changed
- **BUG-23**: 400/404 on a model now falls back to the other model (401/403 stop immediately). Exhaustion raises a
  retryable error that carries the last status (no more "Last error: None"). Retries use `GROQ_MAX_RETRIES` and a
  total deadline (`GROQ_TOTAL_DEADLINE_SECONDS`, default 45). RPM/TPM come from config, and the token tracker no
  longer caps the recorded estimate at 1200. Empty `GROQ_API_KEY`: fails fast per call, and startup refuses to run
  outside development. Bad JSON is wrapped in `GroqClientError`. The false "mock/degraded mode" claim is removed.
- **BUG-24**: prompts are real f-strings; token budget 900 -> 2500. Empty or invalid output raises `RoadmapValidationError`
  (502, rolled back; the previous active roadmap is untouched because deactivation happens after generation).
  Sanitizer now trims over-budget weeks, adds missing week 1/2 modules, adds a week-2 revision lesson, clears
  future-week lessons, drops modules past `total_duration_weeks`, and the result is re-validated. Prerequisites are persisted.
- **BUG-25**: one `set_lesson_status` updates lesson, `completed_lessons` and schedule rows together. Used by
  `PUT /roadmaps/lessons/{id}/status` and `PUT /schedule/{id}/status`. `lesson_agent` now moves `pending` -> `in_progress`.
- **BUG-27**: sliding-window limits per user/IP on login, register, goals, lessons (generate/doubt/quiz/submit), cycle,
  voice, notes upload/search; login lockout after 5 failures per email+IP in 15 min; daily LLM-call budget per user
  (`USER_DAILY_LLM_CALLS`). Disable with `RATE_LIMIT_ENABLED=false`.
- **BUG-28**: max lengths, `Literal` enums (levels, voice, sort_by, explanation depth), bounds (`daily_minutes` 10-480, speed 0.5-2.0),
  LIKE/ILIKE escaping everywhere (`escape_like`).
- **BUG-29**: `ApiError` with status; 422 detail arrays are formatted; 401 on an authenticated call logs the user out via an event;
  network blips and 5xx no longer wipe the token; only a 404 means "no roadmap"; per-request timeouts (30s, 150s for LLM routes).
- **Frontend contract**: doubt `/doubt`; quiz POST generate and `/lessons/{id}/quiz/submit` with `question_index/selected_option/written_answer`;
  lesson `heading/content` mapped; quiz options dict -> ordered array with real letters; score from `overall_score`; notes upload sends `subject`
  and `visibility`, reads `chunks_created`, `text_content`, `visibility`; schedule via `GET /schedule?roadmap_id=`, generate then reload, status via
  `PUT /schedule/{id}/status`; votes send `vote_value`, report reads `total_reports/quarantined`, sort `latest`, publish sends `visibility`;
  voice reads `{text}`, sends the recorder's real mime type, stops mic tracks; ErrorBoundary added; the "adaptive replanning" message now reads `adaptation.action`.

## Not done / deliberate
- **BUG-23, DB session during LLM calls**: the request still holds its DB session while Groq runs. The deadline bounds it to ~45s; releasing it needs a service refactor.
- **BUG-27**: limits are per process. With several workers use Redis (swap `_store` in `api/rate_limit.py`).
- **BUG-29, JWT in localStorage / no refresh / no revocation**: needs an httpOnly-cookie or refresh-token design on the backend. Not changed.
- **BUG-20**: background ingest and a proxy body-size limit are still open (see round-3 notes).
- **Cycle UI**: `LearningCycleModal` still calls the lesson endpoints directly, not `/cycle/*`. The client methods are fixed but unused.
- Schedule rows have no duration field, so the UI shows "Scheduled" instead of minutes.

## Verification
- `tests/test_round4_fixes.py`: 27 passed (`PYTHONPATH=backend pytest tests/test_round4_fixes.py`), no DB or network.
- Frontend: `tsc --noEmit` clean and `vite build` succeeds.
- **Not run**: the round-1/round-3 suites and the phase tests need PostgreSQL + pgvector, and nothing was tested against a live backend or Groq. Run them before merging.
