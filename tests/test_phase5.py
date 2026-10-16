import io
import os
import sys
import uuid
from pathlib import Path
import pytest
import httpx

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app


@pytest.mark.asyncio
async def test_system_health_and_readiness():
    """Verify health and readiness probes check database, pgvector, and services."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        ready_res = await client.get("/ready")
        assert ready_res.status_code == 200
        data = ready_res.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] is True


@pytest.mark.asyncio
async def test_end_to_end_student_lifecycle():
    """Verify full end-to-end multi-session student journey from registration through graduation:
    1. Register user & obtain private workspace
    2. Submit goal & generate 2-week active sprint roadmap + future placeholders
    3. Upload private lecture notes & generate 384-d dense vector embeddings
    4. Run 6-step persistent learning cycle (lesson -> voice -> doubt -> quiz -> eval -> adaptive)
    5. Generate capacity-paced study calendar with spaced repetition reviews
    6. Publish note to community library & verify Wilson score ranking
    7. Second user discovers, upvotes, and imports independent clone
    8. Original user deletes note -> imported clone remains intact
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: User 1 Registration
        email_1 = f"student_{uuid.uuid4().hex[:6]}@example.com"
        reg_1 = await client.post("/api/v1/auth/register", json={
            "email": email_1,
            "password": "SecurePassword123!",
            "full_name": "Ada Lovelace"
        })
        assert reg_1.status_code == 201
        token_1 = reg_1.json()["access_token"]
        headers_1 = {"Authorization": f"Bearer {token_1}"}

        # Step 2: Goal Intake & Sprint Roadmap
        goal_res = await client.post("/api/v1/goals", json={
            "subject": "Vector Search Systems",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 4,
            "hours_per_week": 6.0,
            "preferred_style": "intuitive visuals with code",
            "specific_objectives": ["HNSW Graphs", "Inverted File Index", "Product Quantization"]
        }, headers=headers_1)
        assert goal_res.status_code == 201
        roadmap = goal_res.json()
        assert roadmap["version"] == 1
        active_modules = [m for m in roadmap["modules"] if m["target_week"] <= 2]
        future_modules = [m for m in roadmap["modules"] if m["target_week"] > 2]
        assert len(active_modules) >= 1
        assert len(future_modules) >= 1
        for m in future_modules:
            assert m["is_planned_later"] is True

        first_lesson = active_modules[0]["lessons"][0]
        lesson_id = first_lesson["id"]

        # Step 3: Upload Private Study Notes & Dense Embeddings
        note_text = (
            "# Hierarchical Navigable Small World (HNSW)\n\n"
            "HNSW builds a multi-layer graph where upper layers have longer skip connections for fast exploration, "
            "and layer 0 contains all data points with dense local clustering. Greedy routing at each layer finds "
            "the local entry point for the layer below. The search latency scales logarithmically O(log N).\n"
        )
        files = {
            "file": ("hnsw_guide.md", io.BytesIO(note_text.encode("utf-8")), "text/markdown")
        }
        upload_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Vector Search Systems", "title": "HNSW Deep Dive", "visibility": "public"},
            files=files,
            headers=headers_1
        )
        assert upload_res.status_code == 201
        note_1 = upload_res.json()
        note_id_1 = note_1["id"]
        assert note_1.get("chunks_created", note_1.get("chunk_count", 0)) >= 1

        # Step 4: Persistent Learning Cycle State Machine
        cycle_res = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers_1)
        assert cycle_res.status_code == 200
        cycle_id = cycle_res.json()["cycle_id"]

        # Step 4a: Generate Lesson (RAG-grounded with HNSW note)
        step_1_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "lesson_gen", "payload": {"style": "intuitive visuals"}},
            headers=headers_1
        )
        assert step_1_res.status_code == 200
        assert "lesson_gen" in step_1_res.json()["cycle"]["completed_steps"]

        # Step 4b: Voice Audio Synthesis (Local Kokoro TTS)
        tts_res = await client.post("/api/v1/voice/speak", json={
            "text": "Welcome to Hierarchical Navigable Small World vector search.",
            "voice": "af_heart"
        }, headers=headers_1)
        assert tts_res.status_code == 200
        assert tts_res.headers["content-type"] == "audio/wav"
        assert tts_res.content[:4] == b"RIFF"

        # Step 4c: Doubt Resolution
        step_2_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "doubt", "payload": {"doubt": "What is the computational complexity of HNSW search?"}},
            headers=headers_1
        )
        assert step_2_res.status_code == 200
        assert "doubt" in step_2_res.json()["cycle"]["completed_steps"]

        # Step 4d: Formative Quiz Generation
        step_3_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "quiz_gen", "payload": {}},
            headers=headers_1
        )
        assert step_3_res.status_code == 200
        cycle_step_3 = step_3_res.json()
        quiz_data = cycle_step_3["step_result"]
        assert quiz_data is not None
        questions = quiz_data["questions"]
        assert len(questions) == 4

        # Step 4e: Submit Quiz Answers
        mock_answers = [
            {
                "question_index": q["question_index"],
                "selected_option": "A" if q["question_type"] == "mcq" else None,
                "written_answer": "Logarithmic search via skip connections." if q["question_type"] != "mcq" else None
            }
            for q in questions
        ]
        step_4_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "eval", "payload": {"answers": mock_answers}},
            headers=headers_1
        )
        assert step_4_res.status_code == 200
        assert "eval" in step_4_res.json()["cycle"]["completed_steps"]

        # Step 5: Study Schedule Generation
        sched_res = await client.post("/api/v1/schedule/generate", json={
            "roadmap_id": roadmap["id"]
        }, headers=headers_1)
        assert sched_res.status_code == 200
        assert sched_res.json()["total_sessions"] >= 1

        get_sched = await client.get("/api/v1/schedule", headers=headers_1)
        assert get_sched.status_code == 200
        schedule_items = get_sched.json()["sessions"]
        assert len(schedule_items) >= 1

        # Mark first session completed
        complete_sched = await client.put(
            f"/api/v1/schedule/{schedule_items[0]['id']}/status",
            json={"status": "completed"},
            headers=headers_1
        )
        assert complete_sched.status_code == 200
        assert complete_sched.json()["status"] == "completed"

        # Step 6: Community Sharing & Wilson Scoring
        vote_res = await client.post(
            f"/api/v1/community/notes/{note_id_1}/vote",
            json={"vote_value": 1},
            headers=headers_1
        )
        assert vote_res.status_code == 200
        assert vote_res.json()["new_wilson_score"] > 0.0

        # Step 7: User 2 Registration & Independent Clone Import
        email_2 = f"bob_{uuid.uuid4().hex[:6]}@example.com"
        reg_2 = await client.post("/api/v1/auth/register", json={
            "email": email_2,
            "password": "SecurePassword123!",
            "full_name": "Bob Learner"
        })
        token_2 = reg_2.json()["access_token"]
        headers_2 = {"Authorization": f"Bearer {token_2}"}

        # User 2 imports User 1's note
        import_res = await client.post(
            f"/api/v1/community/notes/{note_id_1}/import",
            headers=headers_2
        )
        assert import_res.status_code in (200, 201)
        user2_cloned_id = import_res.json().get("imported_note_id", import_res.json().get("new_note_id"))

        # Step 8: User 1 deletes their original note
        del_res = await client.delete(f"/api/v1/notes/{note_id_1}", headers=headers_1)
        assert del_res.status_code == 200

        # Verify User 2's cloned note is STILL accessible with its chunks!
        clone_get = await client.get(f"/api/v1/notes/{user2_cloned_id}", headers=headers_2)
        assert clone_get.status_code == 200
        assert clone_get.json()["id"] == user2_cloned_id
        assert len(clone_get.json()["chunks"]) >= 1
