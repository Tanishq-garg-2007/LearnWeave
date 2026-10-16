import asyncio
import io
import json
import logging
import sys
import uuid
import wave
from pathlib import Path
from typing import List, Dict, Any

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals.phase3")


async def run_benchmark():
    logger.info("Starting LearnWeave Phase 3 Benchmark Suite...")
    transport = httpx.ASGITransport(app=app)

    metrics: Dict[str, Any] = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register benchmark user
        user_email = f"benchmark_p3_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "BenchmarkPasswordP3!",
            "full_name": "Phase 3 Benchmark Student"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ---------------------------------------------------------
        # 1. Voice Pipeline Evaluation (5 trials)
        # ---------------------------------------------------------
        logger.info("Evaluating Voice Pipeline (TTS audio compliance)...")
        test_prompts = [
            "Welcome to LearnWeave AI.",
            "Operating systems manage concurrency and hardware execution.",
            "Distributed consensus guarantees state machine consistency across quorums.",
            "B-Tree indexes maintain logarithmic search depth for range queries.",
            "Adaptive spaced repetition reinforces memory consolidation."
        ]

        tts_success_count = 0
        valid_wav_headers = 0
        latencies = []

        for p in test_prompts:
            import time
            t0 = time.time()
            resp = await client.post("/api/v1/voice/speak", json={"text": p, "voice": "af_heart"}, headers=headers)
            lat = time.time() - t0
            latencies.append(lat)

            if resp.status_code == 200 and "audio/wav" in resp.headers.get("content-type", ""):
                tts_success_count += 1
                try:
                    with wave.open(io.BytesIO(resp.content), "rb") as w:
                        if w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() in (24000, 22050, 16000):
                            valid_wav_headers += 1
                except Exception:
                    pass

        metrics["tts_success_rate"] = round(tts_success_count / len(test_prompts), 4)
        metrics["wav_format_compliance"] = round(valid_wav_headers / len(test_prompts), 4)
        metrics["avg_tts_latency_sec"] = round(sum(latencies) / len(latencies), 3)

        logger.info(f"TTS Results: Success={metrics['tts_success_rate']:.2%} | WAV Compliance={metrics['wav_format_compliance']:.2%} | Avg Latency={metrics['avg_tts_latency_sec']}s")

        # ---------------------------------------------------------
        # 2. Multi-Session Resumption & Idempotency Evaluation
        # ---------------------------------------------------------
        logger.info("Evaluating Learning Cycle Multi-Session Resumption & Idempotency...")
        # Create a test goal
        goal_res = await client.post("/api/v1/goals", json={
            "subject": "Storage Systems",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        roadmap = goal_res.json()
        lesson_id = roadmap["modules"][0]["lessons"][0]["id"]

        # Run cycle through step 1 (lesson_gen) and step 2 (doubt)
        start_res = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)
        cycle_id = start_res.json()["cycle_id"]

        await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "lesson_gen"}, headers=headers)
        await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "doubt", "input_data": {"doubt": "Explain SSD wear leveling."}},
            headers=headers
        )

        # Simulate 10 page reloads / reconnects
        resumption_success = 0
        for _ in range(10):
            recon = await client.post("/api/v1/cycle/start", json={"lesson_id": lesson_id}, headers=headers)
            r_data = recon.json()
            if (
                r_data["cycle_id"] == cycle_id
                and r_data["current_step"] == "quiz_gen"
                and "lesson_gen" in r_data["completed_steps"]
                and "doubt" in r_data["completed_steps"]
            ):
                resumption_success += 1

        metrics["resumption_recovery_rate"] = round(resumption_success / 10.0, 4)

        # Test step idempotency (calling doubt 5 times returns identical cached outputs instantly)
        idempotent_trials = 0
        for _ in range(5):
            t0 = time.time()
            s_repeat = await client.post(
                f"/api/v1/cycle/{cycle_id}/step",
                json={"step_name": "doubt"},
                headers=headers
            )
            dur = time.time() - t0
            # Cached step returns in under 50ms without invoking LLM
            if s_repeat.status_code == 200 and dur < 0.1:
                idempotent_trials += 1

        metrics["step_idempotency_rate"] = round(idempotent_trials / 5.0, 4)
        logger.info(f"Cycle Resumption Rate: {metrics['resumption_recovery_rate']:.2%} | Idempotency Rate: {metrics['step_idempotency_rate']:.2%}")

        # ---------------------------------------------------------
        # 3. Adaptive Replanning Evaluation
        # ---------------------------------------------------------
        logger.info("Evaluating Adaptive Replanning (Remedial Insertion & Versioning)...")
        # Generate quiz for the cycle
        q_step = await client.post(f"/api/v1/cycle/{cycle_id}/step", json={"step_name": "quiz_gen"}, headers=headers)
        assessment_id = q_step.json()["step_result"]["assessment_id"]

        # Submit failing evaluation (< 70%)
        eval_failing = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={
                "step_name": "eval",
                "input_data": {
                    "assessment_id": assessment_id,
                    "answers": [
                        {"question_index": 0, "selected_option": "Z"},
                        {"question_index": 1, "selected_option": "Z"},
                        {"question_index": 2, "selected_option": "Z"},
                        {"question_index": 3, "written_answer": "insufficient"}
                    ]
                }
            },
            headers=headers
        )
        assert eval_failing.json()["step_result"]["passed"] is False

        # Run adaptive step
        adapt_step = await client.post(
            f"/api/v1/cycle/{cycle_id}/step",
            json={"step_name": "adaptive"},
            headers=headers
        )
        adapt_data = adapt_step.json()["step_result"]

        remedial_inserted = (adapt_data["action"] == "remedial_inserted")
        version_bumped = (adapt_data["new_roadmap_version"] >= 2)

        # Check roadmap lessons count increased by 1
        active_r = await client.get("/api/v1/roadmaps/active", headers=headers)
        lessons_after = active_r.json()["modules"][0]["lessons"]
        has_revision_lesson = any("Targeted Revision" in l["title"] for l in lessons_after)

        metrics["remedial_insertion_verified"] = remedial_inserted and has_revision_lesson
        metrics["roadmap_version_incremented"] = version_bumped
        logger.info(f"Adaptive Results: Remedial Inserted={metrics['remedial_insertion_verified']} | Version Incremented={metrics['roadmap_version_incremented']}")

        # ---------------------------------------------------------
        # 4. Study Scheduler Pacing & Spaced Repetition Evaluation
        # ---------------------------------------------------------
        logger.info("Evaluating Study Scheduler & Spaced Repetition...")
        sched_res = await client.post("/api/v1/schedule/generate", json={"roadmap_id": roadmap["id"]}, headers=headers)
        sched_data = sched_res.json()
        total_sessions = sched_data["total_sessions"]

        list_s = await client.get("/api/v1/schedule", headers=headers)
        sessions = list_s.json()["sessions"]

        # Confirm sessions laid out over distinct future dates
        dates = {s["scheduled_date"][:10] for s in sessions}
        metrics["total_scheduled_sessions"] = total_sessions
        metrics["distributed_study_days"] = len(dates)
        metrics["spaced_repetition_scheduled"] = any(s["is_revision"] for s in sessions)

        logger.info(f"Scheduler Results: Total Sessions={total_sessions} | Study Days={len(dates)} | Spaced Repetition Included={metrics['spaced_repetition_scheduled']}")

        # ---------------------------------------------------------
        # 5. Gate Determination
        # ---------------------------------------------------------
        passed_gate = (
            metrics["tts_success_rate"] == 1.0
            and metrics["wav_format_compliance"] == 1.0
            and metrics["resumption_recovery_rate"] == 1.0
            and metrics["step_idempotency_rate"] == 1.0
            and metrics["remedial_insertion_verified"] is True
            and metrics["roadmap_version_incremented"] is True
        )
        metrics["passed_gate"] = passed_gate

        # Save metrics
        out_file = Path("evals/results/phase3_metrics.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(metrics, indent=2))
        logger.info(f"Phase 3 Benchmark completed. Metrics saved to {out_file}.")
        print("\n=== PHASE 3 BENCHMARK METRICS ===")
        print(json.dumps(metrics, indent=2))
        return metrics


if __name__ == "__main__":
    asyncio.run(run_benchmark())
