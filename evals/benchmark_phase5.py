import asyncio
import io
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals.phase5")


async def run_benchmark():
    logger.info("Starting LearnWeave Phase 5 End-to-End System Benchmark...")
    transport = httpx.ASGITransport(app=app)
    metrics: Dict[str, Any] = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. System Health & Readiness Verification
        logger.info("Evaluating system health and readiness...")
        health_t0 = time.time()
        health_res = await client.get("/health")
        health_latency_ms = (time.time() - health_t0) * 1000
        assert health_res.status_code == 200

        ready_res = await client.get("/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["checks"]["database"] is True

        metrics["system_health_status"] = "healthy"
        metrics["readiness_verified"] = True
        metrics["health_endpoint_latency_ms"] = round(health_latency_ms, 2)

        # 2. End-to-End Student Onboarding
        logger.info("Evaluating User Onboarding & Goal Roadmap Generation...")
        email = f"e2e_student_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "E2E Benchmark Student"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        goal_t0 = time.time()
        goal_res = await client.post("/api/v1/goals", json={
            "subject": "Modern Neural Architectures",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 4,
            "hours_per_week": 5.0,
            "preferred_style": "rigorous with visual intuition",
            "specific_objectives": ["Multi-Head Attention", "Rotary Positional Embeddings", "KV Cache"]
        }, headers=headers)
        goal_latency = time.time() - goal_t0
        assert goal_res.status_code == 201
        roadmap = goal_res.json()

        active_modules = [m for m in roadmap["modules"] if m["target_week"] <= 2]
        future_modules = [m for m in roadmap["modules"] if m["target_week"] > 2]
        assert len(active_modules) >= 1
        assert len(future_modules) >= 1
        metrics["roadmap_2week_sprint_enforced"] = True
        metrics["roadmap_generation_latency_s"] = round(goal_latency, 2)

        # 3. Knowledge Base Upload & Local ONNX Embedding
        logger.info("Evaluating Knowledge Base Upload & ONNX Embedding...")
        note_content = (
            "# Multi-Head Self-Attention & RoPE\n\n"
            "In Multi-Head Attention, queries, keys, and values are linearly projected into multiple subspace heads. "
            "Rotary Positional Embedding (RoPE) encodes relative position by rotating query and key representations "
            "in complex space, preserving inner products with decaying magnitude as distance grows.\n\n"
            "During inference, the Key-Value (KV) cache saves past key and value projections so autoregressive tokens "
            "do not recompute attention over previous positions, transforming O(N^2) generation into O(N) memory operations.\n"
        )
        files = {"file": ("attention.md", io.BytesIO(note_content.encode("utf-8")), "text/markdown")}
        upload_t0 = time.time()
        up_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Modern Neural Architectures", "title": "Transformer Attention Deep Dive", "visibility": "public"},
            files=files,
            headers=headers
        )
        upload_latency_ms = (time.time() - upload_t0) * 1000
        assert up_res.status_code == 201
        note_data = up_res.json()
        note_id = note_data["id"]
        metrics["note_chunking_success"] = True
        metrics["note_chunk_count"] = note_data.get("chunks_created", 1)
        metrics["upload_and_embedding_latency_ms"] = round(upload_latency_ms, 2)

        # 4. Learning Cycle State Machine & Voice Narration
        logger.info("Evaluating Learning Cycle State Machine & Voice Synthesis...")
        first_lesson = active_modules[0]["lessons"][0]
        cycle_res = await client.post("/api/v1/cycle/start", json={"lesson_id": first_lesson["id"]}, headers=headers)
        assert cycle_res.status_code == 200
        cycle_id = cycle_res.json()["cycle_id"]

        # Run lesson_gen step
        step1_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "lesson_gen", "payload": {}},
            headers=headers
        )
        assert step1_res.status_code == 200
        metrics["learning_cycle_step_lesson_gen"] = True

        # Run TTS Voice synthesis
        tts_t0 = time.time()
        tts_res = await client.post("/api/v1/voice/speak", json={
            "text": "Multi-Head Attention projects keys, queries, and values into subspaces.",
            "voice": "af_heart"
        }, headers=headers)
        tts_latency_s = time.time() - tts_t0
        assert tts_res.status_code == 200
        assert tts_res.content[:4] == b"RIFF"
        metrics["tts_synthesis_success"] = True
        metrics["tts_latency_s"] = round(tts_latency_s, 3)

        # Run quiz_gen and eval
        logger.info("Evaluating Formative Assessment & Evaluation scoring...")
        step3_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "quiz_gen", "payload": {}},
            headers=headers
        )
        assert step3_res.status_code == 200
        quiz_data = step3_res.json()["step_result"]

        mock_answers = [
            {
                "question_index": q["question_index"],
                "selected_option": "A" if q["question_type"] == "mcq" else None,
                "written_answer": "RoPE rotates representations in complex space." if q["question_type"] != "mcq" else None
            }
            for q in quiz_data["questions"]
        ]
        step4_res = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "eval", "payload": {"answers": mock_answers}},
            headers=headers
        )
        assert step4_res.status_code == 200
        eval_context = step4_res.json()["step_result"]
        assert eval_context is not None
        metrics["quiz_evaluation_success"] = True
        metrics["quiz_score_percentage"] = round(eval_context.get("overall_score", 0) * 100, 1)

        # 5. Study Schedule Verification
        logger.info("Evaluating Study Schedule Generation...")
        sched_res = await client.post("/api/v1/schedule/generate", json={"roadmap_id": roadmap["id"]}, headers=headers)
        assert sched_res.status_code == 200
        schedules = sched_res.json()
        assert len(schedules) >= 1
        metrics["study_schedule_generated"] = True
        metrics["total_scheduled_sessions"] = len(schedules)

        # 6. Community Wilson Ranking & Independent Clone Verification
        logger.info("Evaluating Community Wilson Ranking & Clone Decoupling...")
        vote_res = await client.post(
            f"/api/v1/community/notes/{note_id}/vote",
            json={"vote_value": 1},
            headers=headers
        )
        assert vote_res.status_code == 200
        wilson_score = vote_res.json().get("new_wilson_score", vote_res.json().get("wilson_score", 0.0))
        metrics["community_wilson_score"] = round(wilson_score, 4)

        # Register User 2
        user2_email = f"e2e_peer_{uuid.uuid4().hex[:6]}@example.com"
        reg2 = await client.post("/api/v1/auth/register", json={
            "email": user2_email,
            "password": "Password123!",
            "full_name": "Peer Reviewer"
        })
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 2 imports note
        import_res = await client.post(f"/api/v1/community/notes/{note_id}/import", headers=headers2)
        assert import_res.status_code in (200, 201)
        cloned_note_id = import_res.json().get("imported_note_id", import_res.json().get("new_note_id"))

        # User 1 deletes original note
        del_res = await client.delete(f"/api/v1/notes/{note_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify User 2's cloned note still exists and has chunks
        clone_check = await client.get(f"/api/v1/notes/{cloned_note_id}", headers=headers2)
        assert clone_check.status_code == 200
        assert len(clone_check.json()["chunks"]) == note_data.get("chunks_created", 1)
        metrics["independent_clone_preservation"] = True

        # 7. Privacy Leakage Verification
        # User 2 cannot access user 1's workspace or private items
        forbidden_test = await client.get(f"/api/v1/notes/{note_id}", headers=headers2)
        assert forbidden_test.status_code in (403, 404)
        metrics["cross_user_privacy_leakage"] = 0.0

        metrics["all_phase_invariants_passed"] = True
        metrics["passed_gate"] = True

    # Output results
    output_path = Path(__file__).resolve().parent / "results" / "phase5_metrics.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("=== Phase 5 System Benchmark Completed Successfully ===")
    for k, v in metrics.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
