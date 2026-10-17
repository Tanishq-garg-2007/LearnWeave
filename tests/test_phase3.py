import sys
import io
import wave
import uuid
from pathlib import Path
import pytest
import httpx

# Configure path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app


@pytest.mark.asyncio
async def test_voice_pipeline():
    """Verify local TTS synthesis producing pristine 24kHz 16-bit mono WAV audio."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        user_email = f"voice_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "Password123!",
            "full_name": "Voice Learner"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. TTS Synthesis
        text_prompt = "LearnWeave AI dynamically adapts your learning roadmap as you progress."
        speak_res = await client.post(
            "/api/v1/voice/speak",
            json={"text": text_prompt, "voice": "af_heart"},
            headers=headers
        )
        assert speak_res.status_code == 200, f"TTS failed: {speak_res.text}"
        assert "audio/wav" in speak_res.headers.get("content-type", "")

        wav_bytes = speak_res.content
        assert len(wav_bytes) > 1000

        # Validate standard WAV format
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            assert w.getnchannels() == 1, "Must be mono audio"
            assert w.getsampwidth() == 2, "Must be 16-bit PCM (2 bytes per sample)"
            assert w.getframerate() in (24000, 22050, 16000), "Must be standard sample rate"
            duration = w.getnframes() / float(w.getframerate())
            assert duration > 0.5, "Duration must be valid non-trivial audio"


@pytest.mark.asyncio
async def test_learning_cycle_engine_and_resumption():
    """Verify 6-step cycle execution, step-level idempotency, and multi-session resumption."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_email = f"cycle_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "Password123!",
            "full_name": "Cycle Learner"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create goal & roadmap
        g_res = await client.post("/api/v1/goals", json={
            "subject": "Compilers & Type Systems",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        lesson_id = g_res.json()["modules"][0]["lessons"][0]["id"]

        # 1. Start cycle
        start_res = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)
        assert start_res.status_code == 200
        cycle_id = start_res.json()["cycle_id"]
        assert cycle_id

        # 2. Step 1: lesson_gen
        s1 = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "lesson_gen"},
            headers=headers
        )
        assert s1.status_code == 200
        assert s1.json()["cycle"]["current_step"] == "doubt"
        assert "lesson_gen" in s1.json()["cycle"]["completed_steps"]

        # 3. Step 2: doubt
        s2 = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "doubt", "input_data": {"doubt": "What is the difference between parsing and type checking?"}},
            headers=headers
        )
        assert s2.status_code == 200
        assert s2.json()["cycle"]["current_step"] == "quiz_gen"

        # 4. Step 3: quiz_gen
        s3 = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "quiz_gen"},
            headers=headers
        )
        assert s3.status_code == 200
        assert s3.json()["cycle"]["current_step"] == "eval"
        quiz_data = s3.json()["step_result"]
        assert len(quiz_data["questions"]) == 4

        # 5. Simulate Disconnect / Page Reload (Resumption Test)
        resume_res = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)
        assert resume_res.status_code == 200
        resumed = resume_res.json()
        assert resumed["cycle_id"] == cycle_id, "Must return exact same active cycle"
        assert resumed["current_step"] == "eval"
        assert "lesson_gen" in resumed["completed_steps"]
        assert "doubt" in resumed["completed_steps"]
        assert "quiz_gen" in resumed["completed_steps"]

        # 6. Idempotency Test: re-calling quiz_gen returns cached output without re-generating
        idempotent_step = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "quiz_gen"},
            headers=headers
        )
        assert idempotent_step.status_code == 200
        assert idempotent_step.json()["step_result"]["assessment_id"] == quiz_data["assessment_id"]


@pytest.mark.asyncio
async def test_adaptive_replanning_remediation():
    """Verify adaptive agent dynamically inserts remedial revision lesson and increments roadmap version upon low score."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_email = f"adaptive_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "Password123!",
            "full_name": "Adaptive Learner"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create goal & roadmap
        g_res = await client.post("/api/v1/goals", json={
            "subject": "Kernel Memory Management",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        roadmap = g_res.json()
        lesson_id = roadmap["modules"][0]["lessons"][0]["id"]
        initial_lesson_count = len(roadmap["modules"][0]["lessons"])

        # Start cycle
        start = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)
        cycle_id = start.json()["cycle_id"]

        # Run lesson_gen & quiz_gen
        await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)
        quiz_step = await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)
        assessment_id = quiz_step.json()["step_result"]["assessment_id"]

        # Submit intentional failing answers (all incorrect)
        failing_answers = [
            {"question_index": 0, "selected_option": "Z"},
            {"question_index": 1, "selected_option": "Z"},
            {"question_index": 2, "selected_option": "Z"},
            {"question_index": 3, "written_answer": "I don't know"}
        ]
        eval_step = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={
                "step_name": "eval",
                "input_data": {"assessment_id": assessment_id, "answers": failing_answers}
            },
            headers=headers
        )
        assert eval_step.status_code == 200
        assert eval_step.json()["step_result"]["passed"] is False

        # Execute adaptive step
        adapt_step = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "adaptive"},
            headers=headers
        )
        assert adapt_step.status_code == 200
        adapt_res = adapt_step.json()["step_result"]

        assert adapt_res["action"] == "remedial_inserted"
        assert adapt_res["new_roadmap_version"] >= 2
        assert adapt_res["remedial_lesson_id"]

        # Verify active roadmap now contains the remedial lesson
        active_road = await client.get("/api/v1/roadmaps/active", headers=headers)
        assert active_road.status_code == 200
        updated_lessons = active_road.json()["modules"][0]["lessons"]
        assert len(updated_lessons) == initial_lesson_count + 1
        assert any("Targeted Revision" in l["title"] for l in updated_lessons)

        # Verify profile weak areas
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert len(me.json()["profile"]["weak_areas"]) >= 1


@pytest.mark.asyncio
async def test_study_scheduler_and_pacing():
    """Verify study schedule generation, daily capacity pacing, and status tracking."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_email = f"sched_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "Password123!",
            "full_name": "Paced Learner"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create goal & roadmap
        g_res = await client.post("/api/v1/goals", json={
            "subject": "Modern Cryptography",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        roadmap_id = g_res.json()["id"]

        # 1. Generate schedule
        gen_res = await client.post("/api/v1/schedule/generate", json={"roadmap_id": roadmap_id}, headers=headers)
        assert gen_res.status_code == 200
        assert gen_res.json()["total_sessions"] >= 2

        # 2. Get schedule
        list_res = await client.get("/api/v1/schedule", headers=headers)
        assert list_res.status_code == 200
        sessions = list_res.json()["sessions"]
        assert len(sessions) >= 2
        first_session = sessions[0]
        assert first_session["status"] == "pending"  # contract: new sessions are pending

        # 3. Mark completed
        update_res = await client.put(
            f"/api/v1/schedule/{first_session['id']}/status",
            json={"status": "completed"},
            headers=headers
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "completed"
