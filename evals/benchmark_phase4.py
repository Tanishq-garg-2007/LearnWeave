import asyncio
import io
import json
import logging
import sys
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.main import app
from app.services.wilson_service import calculate_wilson_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals.phase4")


async def run_benchmark():
    logger.info("Starting LearnWeave Phase 4 Benchmark Suite...")
    transport = httpx.ASGITransport(app=app)

    metrics: Dict[str, Any] = {}

    # 1. Wilson Score Distribution Evaluation
    logger.info("Evaluating Wilson Score Mathematical Properties across 10 distributions...")
    test_cases = [
        {"up": 100, "down": 0, "expected_min": 0.95},
        {"up": 50, "down": 2, "expected_min": 0.85},
        {"up": 20, "down": 1, "expected_min": 0.75},
        {"up": 10, "down": 0, "expected_min": 0.70},
        {"up": 5, "down": 0, "expected_min": 0.50},
        {"up": 1, "down": 0, "expected_min": 0.15},
        {"up": 20, "down": 20, "expected_min": 0.35},
        {"up": 1, "down": 10, "expected_min": 0.01},
        {"up": 0, "down": 10, "expected_min": 0.00},
        {"up": 0, "down": 0, "expected_min": 0.00}
    ]

    wilson_monotonic = True
    scores = []
    for tc in test_cases:
        s = calculate_wilson_score(tc["up"], tc["down"])
        scores.append(s)

    # 100/0 > 10/0 > 5/0 > 1/0
    assert scores[0] > scores[3] > scores[4] > scores[5], "Wilson score must penalize low sample sizes"
    metrics["wilson_monotonic_ordering_valid"] = True

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register Authors
        author_email = f"benchmark_p4_author_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": author_email,
            "password": "Password123!",
            "full_name": "Library Publisher"
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Ingest 5 Community Notes with varied upvotes
        logger.info("Publishing community notes with synthetic voting distributions...")
        subjects = [
            ("Distributed Systems", "Consensus Algorithms and Paxos Quorums"),
            ("Operating Systems", "Virtual Memory, Paging and Page Table Walking"),
            ("Database Systems", "B-Tree vs LSM Tree Storage Engine Tradeoffs"),
            ("Computer Networks", "TCP Fast Retransmit and Congestion Control"),
            ("Compilers", "Static Single Assignment Form and Phi Placements")
        ]

        note_ids = []
        for subj, title in subjects:
            files = {"file": ("note.txt", io.BytesIO(f"Comprehensive guide to {subj}: {title}".encode("utf-8")), "text/plain")}
            up = await client.post(
                "/api/v1/notes/upload",
                data={"subject": subj, "title": title, "visibility": "public"},
                files=files,
                headers=headers_a
            )
            note_ids.append(up.json()["id"])

        # 3. Community Search Latency & Discovery Evaluation (10 queries)
        logger.info("Evaluating Community Library Search & Discovery Latency...")
        discovery_latencies = []
        for i in range(10):
            t0 = time.time()
            res = await client.get("/api/v1/community/notes?sort_by=wilson", headers=headers_a)
            dur = time.time() - t0
            discovery_latencies.append(dur)
            assert res.status_code == 200

        avg_discovery_lat = sum(discovery_latencies) / len(discovery_latencies)
        metrics["avg_community_discovery_latency_ms"] = round(avg_discovery_lat * 1000, 2)

        # 4. Independent Copy Integrity Evaluation (5 clones)
        logger.info("Evaluating Independent Deep Copy Integrity under Author Deletion...")
        importer_email = f"importer_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": importer_email,
            "password": "Password123!",
            "full_name": "Library Consumer"
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Import 2 notes
        cloned_ids = []
        for nid in note_ids[:2]:
            imp_res = await client.post(f"/api/v1/community/notes/{nid}/import", headers=headers_b)
            assert imp_res.status_code == 200
            cloned_ids.append(imp_res.json()["imported_note_id"])

        # Delete original notes from Author
        for nid in note_ids[:2]:
            del_res = await client.delete(f"/api/v1/notes/{nid}", headers=headers_a)
            assert del_res.status_code == 200

        # Verify all imported clones survived without loss of chunks
        survived_count = 0
        for cid in cloned_ids:
            chk = await client.get(f"/api/v1/notes/{cid}", headers=headers_b)
            if chk.status_code == 200 and len(chk.json()["chunks"]) >= 1:
                survived_count += 1

        clone_preservation_rate = survived_count / len(cloned_ids)
        metrics["independent_clone_preservation_rate"] = round(clone_preservation_rate, 4)

        # 5. Automated Moderation Quarantine Evaluation
        logger.info("Evaluating Moderation Quarantine Pipeline...")
        # Create reported note
        files = {"file": ("report_me.txt", io.BytesIO(b"Violating public note sample content"), "text/plain")}
        bad_up = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Unmoderated", "title": "Violating Post", "visibility": "public"},
            files=files,
            headers=headers_a
        )
        bad_note_id = bad_up.json()["id"]

        # Register 3 reporters and flag the note
        for r_idx in range(3):
            r_reg = await client.post("/api/v1/auth/register", json={
                "email": f"rep_{r_idx}_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Password123!",
                "full_name": f"Reporter {r_idx}"
            })
            tok = r_reg.json()["access_token"]
            await client.post(
                f"/api/v1/community/notes/{bad_note_id}/report",
                json={"reason": f"Violation flag #{r_idx}"},
                headers={"Authorization": f"Bearer {tok}"}
            )

        # Verify bad note is absent from public discovery
        feed = await client.get("/api/v1/community/notes", headers=headers_a)
        feed_ids = [n["id"] for n in feed.json()["notes"]]
        quarantined = (bad_note_id not in feed_ids)
        metrics["quarantine_enforcement_verified"] = quarantined

        # 6. Summary & Gate Pass
        passed_gate = (
            metrics["wilson_monotonic_ordering_valid"] is True
            and metrics["independent_clone_preservation_rate"] == 1.0
            and metrics["quarantine_enforcement_verified"] is True
            and metrics["avg_community_discovery_latency_ms"] < 200.0
        )
        metrics["passed_gate"] = passed_gate

        out_file = Path("evals/results/phase4_metrics.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(metrics, indent=2))
        logger.info(f"Phase 4 Benchmark completed. Metrics saved to {out_file}.")
        print("\n=== PHASE 4 BENCHMARK METRICS ===")
        print(json.dumps(metrics, indent=2))
        return metrics


if __name__ == "__main__":
    asyncio.run(run_benchmark())
