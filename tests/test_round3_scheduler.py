"""Round 3 scheduler tests (BUG-19): ownership, scope, status handling, and reviews.

The LLM is replaced by the same deterministic stand-in used in test_round1_fixes.py,
so these tests do not need a Groq key or network access.
"""
import json
import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.db.models import LearnerProfile, StudySchedule, User  # noqa: E402
from app.services.groq_client import GroqClient, GroqClientError  # noqa: E402


# ---------------------------------------------------------------------------
# Deterministic LLM stand-in (same contract as test_round1_fixes.py)
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
                     "duration_minutes": 45, "prerequisite_titles": [], "is_revision": (w == 2)},
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utc_today():
    return datetime.now(timezone.utc).date()


async def _register(client, prefix="user"):
    """Return (auth headers, email). The email is used for direct database setup."""
    email = _email(prefix)
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "full_name": prefix
    })
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, email


async def _create_goal(client, headers) -> dict:
    res = await client.post("/api/v1/goals", json={
        "subject": "Test Subject",
        "target_level": "intermediate",
        "current_level": "beginner",
        "total_duration_weeks": 2,
        "hours_per_week": 4.0,
    }, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _lesson_ids(roadmap: dict) -> list:
    return [lesson["id"] for module in roadmap["modules"] for lesson in module["lessons"]]


async def _sessions(client, headers, roadmap_id=None, upcoming_only: bool = False) -> list:
    params = {}
    if roadmap_id is not None:
        params["roadmap_id"] = roadmap_id
    if upcoming_only:
        params["upcoming_only"] = "true"
    res = await client.get("/api/v1/schedule", params=params, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["sessions"]


async def _generate(client, headers, roadmap_id):
    return await client.post("/api/v1/schedule/generate", json={"roadmap_id": roadmap_id}, headers=headers)


async def _user_id(email: str) -> str:
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(User.id).where(User.email == email))).scalar_one()


async def _set_profile(email: str, **values) -> None:
    user_id = await _user_id(email)
    async with AsyncSessionLocal() as db:
        await db.execute(update(LearnerProfile).where(LearnerProfile.user_id == user_id).values(**values))
        await db.commit()


async def _insert_session(email: str, lesson_id: str, status: str, when: datetime) -> None:
    user_id = await _user_id(email)
    async with AsyncSessionLocal() as db:
        db.add(StudySchedule(user_id=user_id, lesson_id=lesson_id, scheduled_date=when, status=status))
        await db.commit()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

async def test_generate_for_foreign_roadmap_is_404_and_schedules_nothing(client):
    owner_headers, _ = await _register(client, "owner")
    other_headers, _ = await _register(client, "other")
    owner_roadmap = await _create_goal(client, owner_headers)

    before = sorted(s["id"] for s in await _sessions(client, owner_headers))
    assert before, "goal creation should already have scheduled the owner's lessons"

    res = await _generate(client, other_headers, owner_roadmap["id"])
    assert res.status_code == 404, res.text

    # Nothing was scheduled for the other user, and the owner's rows are untouched.
    assert await _sessions(client, other_headers) == []
    assert sorted(s["id"] for s in await _sessions(client, owner_headers)) == before


async def test_get_schedule_lists_only_callers_sessions(client):
    a_headers, a_email = await _register(client, "list_a")
    b_headers, _ = await _register(client, "list_b")
    a_roadmap = await _create_goal(client, a_headers)
    b_roadmap = await _create_goal(client, b_headers)

    a_ids = {s["id"] for s in await _sessions(client, a_headers)}
    b_ids = {s["id"] for s in await _sessions(client, b_headers)}
    assert a_ids and b_ids and a_ids.isdisjoint(b_ids)

    # A roadmap_id filter that points at someone else's roadmap returns nothing.
    assert await _sessions(client, a_headers, roadmap_id=b_roadmap["id"]) == []
    assert {s["id"] for s in await _sessions(client, a_headers, roadmap_id=a_roadmap["id"])} == a_ids

    # A legacy row (written by the old bug) that points at another user's lesson stays hidden,
    # and the owner cannot change it either.
    foreign_lesson = _lesson_ids(b_roadmap)[0]
    await _insert_session(a_email, foreign_lesson, "pending", _utc_now() + timedelta(days=5))
    listed = await _sessions(client, a_headers)
    assert all(s["lesson_id"] != foreign_lesson for s in listed)
    assert {s["id"] for s in listed} == a_ids


# ---------------------------------------------------------------------------
# Scope: only the target roadmap's open rows are replaced
# ---------------------------------------------------------------------------

async def test_generate_keeps_rows_that_belong_to_other_roadmaps(client):
    headers, email = await _register(client, "scope")
    first = await _create_goal(client, headers)
    second = await _create_goal(client, headers)  # second becomes active, first is retired
    first_lesson = _lesson_ids(first)[0]

    # Rows for an inactive roadmap: one open, one completed history row.
    later = _utc_now() + timedelta(days=30)
    await _insert_session(email, first_lesson, "pending", later)
    await _insert_session(email, first_lesson, "completed", later)

    res = await _generate(client, headers, second["id"])
    assert res.status_code == 200, res.text

    sessions = await _sessions(client, headers)
    kept = sorted(s["status"] for s in sessions if s["lesson_id"] == first_lesson)
    assert kept == ["completed", "pending"]

    # The active roadmap has exactly one fresh open session per lesson.
    active = [s for s in sessions if s["lesson_id"] in set(_lesson_ids(second))]
    assert len(active) == len(_lesson_ids(second))

    # The inactive roadmap cannot be regenerated, and its rows stay as they were.
    stale = await _generate(client, headers, first["id"])
    assert stale.status_code == 404, stale.text
    assert sorted(s["status"] for s in await _sessions(client, headers) if s["lesson_id"] == first_lesson) == ["completed", "pending"]


async def test_new_active_roadmap_drops_previous_pending_sessions_but_keeps_history(client):
    headers, _ = await _register(client, "switch")
    first = await _create_goal(client, headers)
    done = (await _sessions(client, headers))[0]
    res = await client.put(f"/api/v1/schedule/{done['id']}/status", json={"status": "completed"}, headers=headers)
    assert res.status_code == 200, res.text

    second = await _create_goal(client, headers)
    remaining = await _sessions(client, headers)

    old = [s for s in remaining if s["lesson_id"] in set(_lesson_ids(first))]
    assert [s["id"] for s in old] == [done["id"]]
    assert old[0]["status"] == "completed"

    new = [s for s in remaining if s["lesson_id"] in set(_lesson_ids(second))]
    assert len(new) == len(_lesson_ids(second))


# ---------------------------------------------------------------------------
# Lesson status filter
# ---------------------------------------------------------------------------

async def test_generate_does_not_schedule_completed_or_skipped_lessons(client):
    headers, _ = await _register(client, "finished")
    roadmap = await _create_goal(client, headers)
    lessons = _lesson_ids(roadmap)
    done_id, skipped_id = lessons[0], lessons[1]

    for lesson_id, new_status in ((done_id, "completed"), (skipped_id, "skipped")):
        res = await client.put(
            f"/api/v1/roadmaps/lessons/{lesson_id}/status",
            json={"new_status": new_status},
            headers=headers,
        )
        assert res.status_code == 200, res.text

    res = await _generate(client, headers, roadmap["id"])
    assert res.status_code == 200, res.text

    scheduled_ids = {s["lesson_id"] for s in await _sessions(client, headers, upcoming_only=True)}
    assert done_id not in scheduled_ids
    assert skipped_id not in scheduled_ids
    assert scheduled_ids == set(lessons[2:])


# ---------------------------------------------------------------------------
# Pacing and spaced repetition
# ---------------------------------------------------------------------------

async def test_generate_packs_lessons_by_daily_minutes_from_tomorrow_at_18_utc(client):
    headers, _ = await _register(client, "minutes")
    res = await client.put("/api/v1/auth/profile", json={"daily_minutes": 90}, headers=headers)
    assert res.status_code == 200, res.text
    await _create_goal(client, headers)

    # Four 45-minute lessons at 90 minutes per day means two lessons on each of two days.
    dates = sorted(datetime.fromisoformat(s["scheduled_date"]) for s in await _sessions(client, headers))
    assert len(dates) == 4
    days = sorted({d.date() for d in dates})
    today = _utc_today()
    assert days == [today + timedelta(days=1), today + timedelta(days=2)]
    assert [d.date() for d in dates].count(days[0]) == 2
    assert all(d.time() == time(18, 0) for d in dates)


async def test_weak_area_reviews_match_exact_titles_and_use_the_study_slot(client):
    headers, email = await _register(client, "weak")
    roadmap = await _create_goal(client, headers)
    lessons = _lesson_ids(roadmap)  # W1 A, W1 B, W2 A, W2 B
    # weak_areas hold lesson titles verbatim. "Week 2" is a partial title and must not match.
    await _set_profile(email, weak_areas=["Week 2", "Week 1 Lesson B"], topic_mastery={"Week 1 Lesson B": 0.2})

    res = await _generate(client, headers, roadmap["id"])
    assert res.status_code == 200, res.text
    sessions = await _sessions(client, headers)

    assert sum(1 for s in sessions if s["lesson_id"] == lessons[2]) == 1

    # The exact title gets its normal session plus reviews at +3 and +7 days.
    b_sessions = [s for s in sessions if s["lesson_id"] == lessons[1]]
    assert len(b_sessions) == 3
    today = _utc_today()
    b_dates = {datetime.fromisoformat(s["scheduled_date"]).date() for s in b_sessions}
    assert {today + timedelta(days=3), today + timedelta(days=7)} <= b_dates

    # Every lesson and review session sits on the 18:00 UTC slot.
    assert all(s["scheduled_date"].endswith("T18:00:00") for s in sessions)


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

async def test_session_status_accepts_only_pending_completed_skipped(client):
    headers, _ = await _register(client, "status")
    other_headers, _ = await _register(client, "status_other")
    await _create_goal(client, headers)
    session = (await _sessions(client, headers))[0]
    url = f"/api/v1/schedule/{session['id']}/status"

    bogus = await client.put(url, json={"status": "bogus"}, headers=headers)
    assert bogus.status_code == 422, bogus.text
    assert isinstance(bogus.json()["detail"], list)

    foreign = await client.put(url, json={"status": "completed"}, headers=other_headers)
    assert foreign.status_code == 404, foreign.text

    done = await client.put(url, json={"status": "completed"}, headers=headers)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["id"] == session["id"]
    assert body["status"] == "completed"
    assert body["lesson_id"] == session["lesson_id"]

    for value in ("skipped", "pending"):
        ok = await client.put(url, json={"status": value}, headers=headers)
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == value
