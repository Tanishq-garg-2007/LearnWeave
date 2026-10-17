"""Regression tests for the round 1 security and integrity fixes.

The LLM is replaced by a deterministic stand-in (see _fake_payload), so these tests
do not need a Groq key or network access.
"""
import asyncio
import io
import json
import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services import groq_client as groq_module  # noqa: E402
from app.services.groq_client import GroqClient, GroqClientError  # noqa: E402
from app.services.doubt_agent import doubt_agent  # noqa: E402
from app.services.quiz_agent import quiz_agent  # noqa: E402
from app.services.embedding_service import embedding_service  # noqa: E402
from app.services.retrieval_service import retriever  # noqa: E402


# ---------------------------------------------------------------------------
# Deterministic LLM stand-in
# ---------------------------------------------------------------------------

def _fake_payload(messages):
    system = messages[0]["content"]
    user = messages[-1]["content"]
    if "curriculum architect" in system:
        weeks = 2
        modules = []
        for w in range(1, weeks + 1):
            modules.append({
                "title": f"Week {w} Core Module",
                "description": "Core concepts.",
                "target_week": w,
                "is_planned_later": False,
                "estimated_hours": 2.0,
                "lessons": [
                    {"title": f"Week {w} Lesson A", "learning_objectives": ["Basics"],
                     "duration_minutes": 45, "prerequisite_titles": [], "is_revision": False},
                    {"title": f"Week {w} Lesson B", "learning_objectives": ["Practice"],
                     "duration_minutes": 45, "prerequisite_titles": [], "is_revision": False},
                ],
            })
        return {"title": "Roadmap", "subject": "Test", "overview": "Overview",
                "modules": modules, "total_estimated_weeks": weeks}
    if '"sections"' in system and '"key_takeaways"' in system:
        return {"title": "Lesson", "summary": "Summary.",
                "sections": [{"heading": "S1", "content": "Body.", "cited_chunk_ids": []}],
                "key_takeaways": ["Takeaway"]}
    if '"questions"' in system:
        qs = [{"question_index": i, "question_type": "mcq", "question": f"Q{i}?",
               "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
               "correct_answer": "A", "explanation": "Because."} for i in range(3)]
        qs.append({"question_index": 3, "question_type": "short_answer", "question": "Explain.",
                   "ideal_answer": "Ideal answer text.", "rubric_criteria": ["Core"]})
        return {"title": "Quiz", "questions": qs}
    if "academic grader" in system or "criteria_met" in system:
        return {"score": 0.9, "feedback": "Good.", "criteria_met": []}
    if '"cited_chunk_ids"' in system and '"answer"' in system:
        return {"answer": f"Answer for: {user[-60:]}", "cited_chunk_ids": []}
    raise GroqClientError("unrecognised schema in test stand-in", retryable=False)


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    async def fake_chat_completion(self, messages, *args, **kwargs):
        return {"choices": [{"message": {"content": json.dumps(_fake_payload(messages))}}]}

    monkeypatch.setattr(GroqClient, "chat_completion", fake_chat_completion)


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register(client, prefix="user"):
    email = _email(prefix)
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "full_name": prefix
    })
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_goal_and_lessons(client, headers):
    res = await client.post("/api/v1/goals", json={
        "subject": "Test Subject",
        "target_level": "intermediate",
        "current_level": "beginner",
        "total_duration_weeks": 2,
        "hours_per_week": 4.0,
    }, headers=headers)
    assert res.status_code == 201, res.text
    lessons = res.json()["modules"][0]["lessons"]
    return [l["id"] for l in lessons]


async def _upload_note(client, headers, visibility):
    files = {"file": ("note.txt", io.BytesIO(b"Some study notes about the topic."), "text/plain")}
    res = await client.post(
        "/api/v1/notes/upload",
        data={"subject": "General", "title": f"Note {visibility}", "visibility": visibility},
        files=files,
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------------------------------------------------------------------------
# BUG-01: lesson ownership
# ---------------------------------------------------------------------------

async def test_foreign_lesson_returns_404_on_every_lesson_route(client):
    owner = await _register(client, "owner")
    other = await _register(client, "other")
    lesson_id = (await _create_goal_and_lessons(client, owner))[0]

    routes = [
        ("POST", f"/api/v1/lessons/{lesson_id}/generate", None),
        ("GET", f"/api/v1/lessons/{lesson_id}", None),
        ("POST", f"/api/v1/lessons/{lesson_id}/doubt", {"doubt": "Why does this work?"}),
        ("GET", f"/api/v1/lessons/{lesson_id}/quiz", None),
        ("POST", f"/api/v1/lessons/{lesson_id}/quiz/submit", {"answers": []}),
        ("GET", f"/api/v1/lessons/{lesson_id}/attempts", None),
        ("POST", "/api/v1/cycle/start", {"lesson_id": lesson_id}),
    ]
    for method, url, body in routes:
        res = await client.request(method, url, json=body, headers=other)
        assert res.status_code == 404, f"{method} {url} leaked a foreign lesson: {res.status_code} {res.text}"

    # The other user's requests must not have written anything into the owner's lesson.
    owned = await client.get(f"/api/v1/lessons/{lesson_id}", headers=owner)
    assert owned.status_code == 200
    assert "sections" not in (owned.json()["lesson_content"] or {})


# ---------------------------------------------------------------------------
# BUG-02: cycle start validation and cycle-bound grading
# ---------------------------------------------------------------------------

async def test_cycle_start_rejects_unknown_lesson_with_404(client):
    headers = await _register(client, "cyc404")
    res = await client.post("/api/v1/cycle/start", json={"lesson_id": str(uuid.uuid4())}, headers=headers)
    assert res.status_code == 404


async def test_eval_step_grades_against_the_cycles_own_assessment(client):
    headers = await _register(client, "evalbind")
    lesson_id = (await _create_goal_and_lessons(client, headers))[0]
    cycle_id = (await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)).json()["cycle_id"]

    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)).status_code == 200
    quiz = await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)
    assert quiz.status_code == 200
    own_assessment_id = quiz.json()["step_result"]["assessment_id"]

    answers = [{"question_index": i, "selected_option": "A"} for i in range(3)]
    answers.append({"question_index": 3, "written_answer": "Some answer text here."})
    res = await client.post(
        f"/api/v1/cycle/{cycle_id}/step",
        json={"step_name": "eval", "input_data": {
            "answers": answers,
            "assessment_id": str(uuid.uuid4()),  # client-supplied id must be ignored
        }},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["step_result"]["assessment_id"] == own_assessment_id


# ---------------------------------------------------------------------------
# BUG-16: step ordering, client errors, and resumable failures
# ---------------------------------------------------------------------------

async def test_cycle_steps_must_run_in_order(client):
    headers = await _register(client, "order")
    lesson_id = (await _create_goal_and_lessons(client, headers))[0]
    cycle_id = (await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)).json()["cycle_id"]

    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)).status_code == 409
    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "adaptive"}, headers=headers)).status_code == 409
    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "not_a_step"}, headers=headers)).status_code == 400

    # Client mistakes must not kill the cycle: it is still running and can continue.
    status_res = await client.get(f"/api/v1/cycle/{cycle_id}", headers=headers)
    assert status_res.json()["status"] == "running"
    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)).status_code == 200


async def test_failed_step_is_recorded_generically_and_can_be_retried(client, monkeypatch):
    headers = await _register(client, "retry")
    lesson_id = (await _create_goal_and_lessons(client, headers))[0]
    cycle_id = (await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)).json()["cycle_id"]
    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)).status_code == 200

    secret = "internal-db-detail-7f3a"
    original_generate_quiz = quiz_agent.generate_quiz

    async def broken_quiz(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(quiz_agent, "generate_quiz", broken_quiz)
    res = await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)
    assert res.status_code == 500
    assert secret not in res.text
    assert "reference:" in res.json()["detail"]

    status_res = await client.get(f"/api/v1/cycle/{cycle_id}", headers=headers)
    assert status_res.json()["status"] == "running"
    assert secret not in (status_res.json()["error_message"] or "")

    monkeypatch.setattr(quiz_agent, "generate_quiz", original_generate_quiz)
    retry = await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)
    assert retry.status_code == 200


async def test_concurrent_cycle_starts_converge_on_one_cycle(client):
    headers = await _register(client, "race")
    lesson_id = (await _create_goal_and_lessons(client, headers))[0]

    plain = await asyncio.gather(*[
        client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers) for _ in range(5)
    ])
    assert all(r.status_code == 200 for r in plain), [r.text for r in plain]
    assert len({r.json()["cycle_id"] for r in plain}) == 1

    keyed = await asyncio.gather(*[
        client.post("/api/v1/cycle/start",
                    json={"lesson_id": lesson_id, "idempotency_key": "race-key"}, headers=headers)
        for _ in range(4)
    ])
    assert all(r.status_code == 200 for r in keyed), [r.text for r in keyed]
    assert len({r.json()["cycle_id"] for r in keyed}) == 1


# ---------------------------------------------------------------------------
# BUG-17: idempotency keys are scoped per user
# ---------------------------------------------------------------------------

async def test_idempotency_keys_are_scoped_per_user(client):
    alice = await _register(client, "idem_a")
    bob = await _register(client, "idem_b")
    alice_lessons = await _create_goal_and_lessons(client, alice)
    bob_lessons = await _create_goal_and_lessons(client, bob)

    a = await client.post("/api/v1/cycle/start",
                          json={"lesson_id": alice_lessons[0], "idempotency_key": "start-lesson-1"}, headers=alice)
    b = await client.post("/api/v1/cycle/start",
                          json={"lesson_id": bob_lessons[0], "idempotency_key": "start-lesson-1"}, headers=bob)
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)
    assert a.json()["cycle_id"] != b.json()["cycle_id"]

    replay = await client.post("/api/v1/cycle/start",
                               json={"lesson_id": alice_lessons[0], "idempotency_key": "start-lesson-1"}, headers=alice)
    assert replay.status_code == 200
    assert replay.json()["cycle_id"] == a.json()["cycle_id"]

    reuse_other_lesson = await client.post("/api/v1/cycle/start",
                                           json={"lesson_id": alice_lessons[1], "idempotency_key": "start-lesson-1"},
                                           headers=alice)
    assert reuse_other_lesson.status_code == 409


# ---------------------------------------------------------------------------
# Doubt answers are cached per question, not per cycle
# ---------------------------------------------------------------------------

async def test_doubt_cache_is_keyed_by_question_text(client, monkeypatch):
    headers = await _register(client, "doubtcache")
    lesson_id = (await _create_goal_and_lessons(client, headers))[0]
    cycle_id = (await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)).json()["cycle_id"]
    assert (await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)).status_code == 200

    calls = []
    original = doubt_agent.resolve_doubt

    async def spy(**kwargs):
        calls.append(kwargs["doubt_text"])
        return await original(**kwargs)

    monkeypatch.setattr(doubt_agent, "resolve_doubt", spy)

    async def doubt(text_value):
        return await client.post(f"/api/v1/cycle/{cycle_id}/step", json={
            "step_name": "doubt", "input_data": {"doubt": text_value}}, headers=headers)

    assert (await doubt("First question?")).status_code == 200
    assert (await doubt("First question?")).status_code == 200  # identical question: served from cache
    assert (await doubt("Second question?")).status_code == 200  # different question: must run
    assert calls == ["First question?", "Second question?"]


# ---------------------------------------------------------------------------
# BUG-13: retrieval failures are contained and reported
# ---------------------------------------------------------------------------

async def test_savepoint_keeps_session_usable_after_failed_statement():
    async with AsyncSessionLocal() as db:
        with pytest.raises(Exception):
            async with retriever._savepoint(db):
                await db.execute(text("SELECT * FROM table_that_does_not_exist_round1"))
        assert (await db.execute(text("SELECT 1"))).scalar() == 1


async def test_dense_leg_failure_is_reported_as_degraded(monkeypatch):
    def broken_embed(_text):
        raise RuntimeError("embedding backend down")

    monkeypatch.setattr(embedding_service, "embed_text", broken_embed)
    async with AsyncSessionLocal() as db:
        result = await retriever.retrieve_detailed(db=db, query="anything at all", user_id=str(uuid.uuid4()))
    assert result.degraded is True
    assert any(e.startswith("dense") for e in result.errors)
    assert result.chunks == []


# ---------------------------------------------------------------------------
# BUG-22: registration and login hardening
# ---------------------------------------------------------------------------

async def test_auth_normalizes_email_and_rejects_oversized_passwords(client):
    base = f"Mixed.Case.{uuid.uuid4().hex[:6]}"

    too_long = await client.post("/api/v1/auth/register", json={
        "email": f"{base}@example.com", "password": "x" * 80})
    assert too_long.status_code == 422

    first = await client.post("/api/v1/auth/register", json={
        "email": f"{base}@Example.com", "password": "Password123!"})
    assert first.status_code == 201

    dup = await client.post("/api/v1/auth/register", json={
        "email": f"{base.lower()}@example.COM", "password": "Password123!"})
    assert dup.status_code == 400

    login = await client.post("/api/v1/auth/login", json={
        "email": f"{base.upper()}@EXAMPLE.com", "password": "Password123!"})
    assert login.status_code == 200

    wrong_pw = await client.post("/api/v1/auth/login", json={
        "email": f"{base}@example.com", "password": "wrong-password"})
    unknown = await client.post("/api/v1/auth/login", json={
        "email": f"nobody.{uuid.uuid4().hex[:6]}@example.com", "password": "wrong-password"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json()["detail"] == unknown.json()["detail"]


# ---------------------------------------------------------------------------
# BUG-10 and BUG-33: community abuse rules and vote consistency
# ---------------------------------------------------------------------------

async def test_owner_cannot_vote_on_own_note_and_votes_toggle(client):
    author = await _register(client, "author")
    voter = await _register(client, "voter")
    note_id = await _upload_note(client, author, "public")

    self_vote = await client.post(f"/api/v1/community/notes/{note_id}/vote", json={"vote_value": 1}, headers=author)
    assert self_vote.status_code == 400

    up = await client.post(f"/api/v1/community/notes/{note_id}/vote", json={"vote_value": 1}, headers=voter)
    assert up.status_code == 200 and up.json()["upvotes"] == 1 and up.json()["wilson_score"] > 0
    again = await client.post(f"/api/v1/community/notes/{note_id}/vote", json={"vote_value": 1}, headers=voter)
    assert again.status_code == 200 and again.json()["upvotes"] == 0  # same button removes the vote


async def test_private_notes_cannot_be_reported_or_voted_by_others(client):
    owner = await _register(client, "privowner")
    stranger = await _register(client, "stranger")
    private_id = await _upload_note(client, owner, "private")

    report = await client.post(f"/api/v1/community/notes/{private_id}/report",
                               json={"reason": "Not a real reason"}, headers=stranger)
    assert report.status_code == 404
    vote = await client.post(f"/api/v1/community/notes/{private_id}/vote", json={"vote_value": 1}, headers=stranger)
    assert vote.status_code == 404


async def test_quarantine_needs_distinct_reporters_and_blocks_republish(client):
    owner = await _register(client, "qowner")
    note_id = await _upload_note(client, owner, "public")
    reporters = [await _register(client, f"qrep{i}") for i in range(3)]

    first = await client.post(f"/api/v1/community/notes/{note_id}/report",
                              json={"reason": "Spam content here"}, headers=reporters[0])
    assert first.status_code == 200 and first.json()["quarantined"] is False

    repeat = await client.post(f"/api/v1/community/notes/{note_id}/report",
                               json={"reason": "Spam content here"}, headers=reporters[0])
    assert repeat.status_code == 409  # one account cannot report the same note twice

    for reporter in reporters[1:]:
        res = await client.post(f"/api/v1/community/notes/{note_id}/report",
                                json={"reason": "Spam content here"}, headers=reporter)
        assert res.status_code == 200
    assert res.json()["quarantined"] is True

    community = await client.get("/api/v1/community/notes", headers=owner)
    assert not any(n["id"] == note_id for n in community.json()["notes"])

    republish = await client.put(f"/api/v1/community/notes/{note_id}/publish",
                                 json={"visibility": "public"}, headers=owner)
    assert republish.status_code == 409


# ---------------------------------------------------------------------------
# BUG-08: production refuses to start with a weak secret or default DB credentials
# ---------------------------------------------------------------------------

def _config_subprocess(env_overrides, drop=()):
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=str(backend_path), env=env, capture_output=True, text=True, timeout=120,
    )


def test_production_refuses_weak_jwt_secret():
    proc = _config_subprocess(
        {"APP_ENV": "production", "JWT_SECRET": "short",
         "DATABASE_URL": "postgresql+asyncpg://app:strong@db:5432/lw",
         "SYNC_DATABASE_URL": "postgresql+psycopg://app:strong@db:5432/lw"},
    )
    assert proc.returncode != 0
    assert "JWT_SECRET must be set" in proc.stderr


def test_production_refuses_default_database_credentials():
    proc = _config_subprocess(
        {"APP_ENV": "production", "JWT_SECRET": secrets.token_urlsafe(48)},
        drop=("DATABASE_URL", "SYNC_DATABASE_URL"),
    )
    assert proc.returncode != 0
    assert "default postgres:postgres credentials" in proc.stderr


def test_development_generates_a_secret_when_unset():
    proc = _config_subprocess({"APP_ENV": "development", "JWT_SECRET": ""})
    assert proc.returncode == 0, proc.stderr
