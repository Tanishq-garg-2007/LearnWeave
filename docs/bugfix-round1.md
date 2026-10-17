# Bug-fix Round 1

Scope: BUG-01, 02, 08, 10, 13, 16, 17, 22, 26, 32, 33 (backend, security and data integrity).

## Operator actions required

1. **Run the new migration**: `cd backend && alembic upgrade head` (revision `7c2e9b1d4f10`).
   It removes duplicate report and active-cycle rows before adding constraints.
2. **Set secrets before deploying** (`.env`):
   - `JWT_SECRET`: at least 32 random characters. Outside `APP_ENV=development` the app refuses to start without it.
   - `POSTGRES_PASSWORD`: required by `docker-compose.yml`. Postgres is now bound to `127.0.0.1` only.
   - Non-development environments also refuse the default `postgres:postgres` database URL.
3. Install dependencies from `backend/requirements.txt`. Test tooling is in `backend/requirements-dev.txt`.
4. If `frontend/dist` was committed to git, run `git rm -r --cached frontend/dist` once, since it is now git-ignored. Run `npm run build` after frontend changes.

## Behaviour changes that clients will notice

| Area | Before | After |
|---|---|---|
| Any lesson route on a lesson the caller does not own | returned data or wrote content | 404 `Lesson not found` |
| `POST /cycle/start` with an unknown lesson | 500 (FK violation) | 404 |
| `POST /cycle/{id}/step` with out-of-order step | silently ran | 409 with the missing prerequisite named |
| `POST /cycle/{id}/step` with unknown step | 400 with internal text | 400 `Unknown step ...` |
| `eval` step | graded against a client-supplied `assessment_id` | graded against the cycle's own quiz only |
| Failed step (server error) | cycle marked `failed` permanently | cycle stays `running`, generic `error_message`, step can be retried |
| Doubt step cache | a second, different question returned the first answer | cached per question text |
| Same `idempotency_key` in two accounts | collided, 500 | scoped per user; reuse for a different lesson gives 409 |
| Concurrent `/cycle/start` calls | duplicate active cycles | exactly one active cycle |
| Register with existing email (any case) | duplicate accounts possible | 400 (race condition: 409) |
| Login | case-sensitive email, no `is_active` check | case-insensitive email, inactive accounts rejected with the same 401 |
| Password over 72 bytes | 500 | 422 |
| Vote on own note | allowed | 400 |
| Vote/report on a private note by another user | allowed (report flipped visibility) | 404 |
| Report the same note twice from one account | counted twice | 409 |
| Quarantine trigger | 3 rows from one account | 3 distinct accounts |
| Owner republishes a quarantined note | allowed | 409 |
| Import of your own note | allowed | 400 |
| Non-public note import | 403 | 404 |
| Error responses | included SQL/driver/upstream Groq text | generic message plus `reference: <id>`; details are in server logs |
| Groq failures | upstream 4xx forwarded as the same status | 503 if retryable, otherwise 502 |
| `/docs`, `/redoc`, `/openapi.json` | public | only when `APP_ENV=development` |

Note that `POST /cycle/{id}/step` for `lesson_gen`, `quiz_gen` and `adaptive` still returns cached output on repeat calls, as before.

## Per-bug summary

- **BUG-01 (IDOR)**: `services/ownership.py` adds `get_owned_lesson` and `get_owned_assessment`, which join through `Roadmap.user_id`. Every lesson route, the lesson/doubt/quiz/evaluation/adaptive agents and the cycle engine use them. `lesson_agent.ensure_lesson_content` is the single cache-or-generate path.
- **BUG-02 (cycle validation)**: lesson ownership is checked before a cycle is created. The eval step uses only the cycle's `quiz_gen` assessment. `NotFoundError` maps to 404 and `StepError` to 400/409.
- **BUG-08 (secrets)**: `config.py` has no default JWT secret. In development an unset secret becomes a random per-process value with a warning. Outside development, startup fails on a weak secret or default DB credentials. `docker-compose.yml` requires `POSTGRES_PASSWORD` and binds to loopback.
- **BUG-10 (community abuse)**: unique `(reporter_id, note_id)` constraint. Reports count distinct accounts, and only public notes can be reported. Self-vote and self-import are forbidden. Quarantined notes cannot be republished. Note rows are locked during vote and report.
- **BUG-13 (retrieval)**: each search runs in a SAVEPOINT (`begin_nested`), so one failing query no longer poisons the session. Failures are logged and reported as `degraded` (`retrieve_detailed`), and degraded lessons are not cached. Doubt and lesson responses carry `retrieval_degraded`.
- **BUG-16 (cycle engine)**: rollback before handling errors. Client mistakes (`StepError`) do not change cycle state. Step prerequisites are enforced. Failed server-side steps leave the cycle resumable.
- **BUG-17 (idempotency)**: `UNIQUE(user_id, idempotency_key)` replaces the global unique key. Replays return the same cycle.
- **BUG-22 (auth)**: email normalization and case-insensitive matching for legacy rows. Byte-aware 72-byte password limit. Duplicate and race handling. Unknown emails spend the same bcrypt time as wrong passwords, and both return the same 401.
- **BUG-26 (error leakage)**: `api/error_utils.py` logs full exceptions under a reference id. Routes return the reference only.
- **BUG-32 (dependencies and deployment)**: `python-jose>=3.4.0`, `passlib` removed (unused), test deps moved to `requirements-dev.txt`, API docs gated to development, `frontend/dist/` git-ignored.
- **BUG-33 (vote transaction)**: one transaction per vote. The note row is locked, the vote, aggregate counts and Wilson score are written together, and `update_note_wilson_score` no longer commits.

## Verification

- `tests/test_round1_fixes.py`: 17 regression tests covering each fix above, including a concurrent `/cycle/start` test.
- Existing suite updated where behaviour was intentionally changed:
  - `test_phase5`: the owner's self-vote now expects 400. The vote is cast by the second user.
- `alembic upgrade head`, `alembic downgrade -1` and `alembic check` (no drift) were run against PostgreSQL 16 + pgvector.
- The LLM was stubbed in tests so the suite runs without network access.
