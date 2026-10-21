import asyncio
import io
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from sqlalchemy import delete
from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models import AssessmentAttempt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals.phase2")

BENCHMARK_CORPUS = [
    {
        "subject": "Operating Systems",
        "title": "CPU Scheduling and Memory Virtualization",
        "content": """
Operating systems employ schedulers to multiplex hardware CPUs among runnable threads.
Preemptive scheduling interrupts executing tasks based on time slice expiry or priority inversion.
Round-robin assigns equal quanta to all active processes in a circular queue.
Multilevel feedback queues adjust process priorities dynamically based on CPU vs I/O burst patterns.
Virtual memory maps process virtual addresses to physical frames using page tables and the Translation Lookaside Buffer (TLB).
When an accessed page is absent from physical RAM, the MMU triggers a page fault interrupt.
"""
    },
    {
        "subject": "Distributed Consensus",
        "title": "Raft Consensus and Quorum Replication",
        "content": """
Raft decomposes distributed consensus into leader election, log replication, and safety.
Nodes exist in follower, candidate, or leader states.
When an election timeout expires without heartbeats, a follower increments its current term and requests votes.
A leader is elected upon acquiring votes from a strict majority quorum of cluster members.
Log entries are committed only after the leader successfully replicates them to a quorum of nodes.
Log matching guarantees that if two logs contain an entry with the same index and term, they are identical up to that point.
"""
    },
    {
        "subject": "Database Engines",
        "title": "B+ Trees and Log-Structured Merge Trees",
        "content": """
B+ Trees store data pointers in sorted leaf nodes linked sequentially for optimal range scans.
All internal nodes in a B+ Tree serve solely as routing index nodes, ensuring balanced logarithmic search depth.
LSM Trees optimize write-intensive workloads by appending mutations sequentially to a Write-Ahead Log and in-memory MemTable.
When the MemTable exceeds its capacity threshold, it is flushed to disk as an immutable SSTable file.
Compaction merges overlapping SSTables and purges tombstones to bound read amplification and reclaim disk space.
"""
    },
    {
        "subject": "Computer Networks",
        "title": "TCP Congestion and Flow Control Mechanisms",
        "content": """
TCP guarantees reliable ordered byte-stream delivery using sequence numbers and cumulative acknowledgments.
Flow control prevents receiver buffer overflow using a sliding receive window advertised in TCP headers.
Congestion control mitigates network core packet drops through slow start, congestion avoidance, and fast retransmit.
The congestion window increases exponentially during slow start until reaching the ssthresh boundary.
Additive-Increase Multiplicative-Decrease adjusts the congestion window linearly upon packet arrival and halves it upon packet loss.
"""
    },
    {
        "subject": "Compiler Design",
        "title": "Intermediate Representations and SSA Form",
        "content": """
Compilers translate source programs through lexical scanning, syntax parsing, and semantic analysis into intermediate code.
Static Single Assignment (SSA) form requires that every variable is defined exactly once.
Phi functions merge conflicting variable values at control-flow join points in the control flow graph.
Dominance frontiers guide optimal phi-node placement in SSA construction.
Register allocation maps unbounded virtual SSA registers to physical CPU registers via graph coloring algorithms.
"""
    }
]

EVAL_QUERIES = [
    # OS
    {"query": "How does preemptive round robin scheduling work?", "subject": "Operating Systems", "keywords": ["preemptive", "round-robin", "quanta", "scheduler"]},
    {"query": "What triggers a page fault in virtual memory?", "subject": "Operating Systems", "keywords": ["page fault", "mmu", "virtual memory", "ram"]},
    {"query": "Role of the Translation Lookaside Buffer TLB", "subject": "Operating Systems", "keywords": ["tlb", "virtual memory", "page"]},
    {"query": "Multilevel feedback queue priority adjustment", "subject": "Operating Systems", "keywords": ["multilevel feedback", "priority", "burst"]},
    {"query": "CPU multiplexing between runnable threads", "subject": "Operating Systems", "keywords": ["multiplex", "scheduler", "cpu"]},
    {"query": "Memory frame mapping and page tables", "subject": "Operating Systems", "keywords": ["page tables", "physical frames", "virtual"]},

    # Consensus
    {"query": "How is a leader elected in the Raft protocol?", "subject": "Distributed Consensus", "keywords": ["raft", "leader election", "candidate", "term"]},
    {"query": "What is a strict majority quorum for committing log entries?", "subject": "Distributed Consensus", "keywords": ["quorum", "replicated", "majority"]},
    {"query": "Raft follower election timeout behavior", "subject": "Distributed Consensus", "keywords": ["timeout", "follower", "candidate"]},
    {"query": "Log matching property guarantees across distributed terms", "subject": "Distributed Consensus", "keywords": ["log matching", "index", "term"]},
    {"query": "Role of AppendEntries heartbeat in suppressing elections", "subject": "Distributed Consensus", "keywords": ["heartbeat", "appendentries", "leader", "raft"]},
    {"query": "State transitions between follower candidate and leader", "subject": "Distributed Consensus", "keywords": ["follower", "candidate", "leader"]},

    # DB Engines
    {"query": "How do B+ Trees optimize range scan operations?", "subject": "Database Engines", "keywords": ["b+ tree", "leaf nodes", "range scans"]},
    {"query": "LSM Tree MemTable flushing to immutable SSTables", "subject": "Database Engines", "keywords": ["memtable", "sstable", "flush"]},
    {"query": "Why do LSM Trees write mutations to a Write-Ahead Log?", "subject": "Database Engines", "keywords": ["write-ahead log", "wal", "lsm"]},
    {"query": "Compaction process for purging tombstones in SSTables", "subject": "Database Engines", "keywords": ["compaction", "tombstones", "sstable"]},
    {"query": "Internal routing nodes vs leaf nodes in balanced trees", "subject": "Database Engines", "keywords": ["internal nodes", "routing", "b+ tree"]},
    {"query": "Write amplification trade-offs in append-only storage engines", "subject": "Database Engines", "keywords": ["write amplification", "lsm", "sstable"]},

    # Networks
    {"query": "How does TCP sliding window flow control prevent buffer overflow?", "subject": "Computer Networks", "keywords": ["sliding window", "flow control", "receive window"]},
    {"query": "Difference between slow start and congestion avoidance in TCP", "subject": "Computer Networks", "keywords": ["slow start", "congestion avoidance", "ssthresh"]},
    {"query": "Additive-Increase Multiplicative-Decrease behavior on packet loss", "subject": "Computer Networks", "keywords": ["additive-increase", "aimd", "halves"]},
    {"query": "Cumulative acknowledgments and sequence numbers in byte streams", "subject": "Computer Networks", "keywords": ["acknowledgments", "sequence numbers", "byte-stream"]},
    {"query": "Fast retransmit upon detecting duplicate acknowledgments", "subject": "Computer Networks", "keywords": ["fast retransmit", "congestion", "tcp"]},
    {"query": "TCP header advertisement of receiver buffer capacity", "subject": "Computer Networks", "keywords": ["advertised", "receive window", "flow control"]},

    # Compilers
    {"query": "Why does Static Single Assignment SSA require single variable definition?", "subject": "Compiler Design", "keywords": ["static single assignment", "ssa", "defined exactly once"]},
    {"query": "What is the purpose of Phi functions at control flow join points?", "subject": "Compiler Design", "keywords": ["phi", "join points", "control flow"]},
    {"query": "How dominance frontiers determine phi-node placement in SSA", "subject": "Compiler Design", "keywords": ["dominance frontiers", "phi", "ssa"]},
    {"query": "Register allocation using graph coloring algorithms", "subject": "Compiler Design", "keywords": ["register allocation", "graph coloring", "registers"]},
    {"query": "Mapping unbounded virtual registers to physical CPU registers", "subject": "Compiler Design", "keywords": ["virtual", "cpu registers", "register allocation"]},
    {"query": "Lexical scanning and AST generation during compiler pipeline", "subject": "Compiler Design", "keywords": ["lexical scanning", "syntax parsing", "intermediate code"]}
]


async def run_benchmark():
    logger.info("Starting LearnWeave Phase 2 Benchmark Suite...")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup User A
        email_a = f"benchmark_a_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "BenchmarkPassword123!",
            "full_name": "Benchmark User A"
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Ingest 5 Documents
        logger.info(f"Ingesting {len(BENCHMARK_CORPUS)} benchmark documents for User A...")
        ingested_count = 0
        total_chunks = 0
        for doc in BENCHMARK_CORPUS:
            files = {
                "file": (f"{doc['subject'].lower().replace(' ', '_')}.md", io.BytesIO(doc["content"].encode("utf-8")), "text/markdown")
            }
            res = await client.post(
                "/api/v1/notes/upload",
                data={"subject": doc["subject"], "title": doc["title"], "visibility": "private"},
                files=files,
                headers=headers_a
            )
            assert res.status_code == 201
            ingested_count += 1
            total_chunks += res.json()["chunks_created"]

        logger.info(f"Ingested {ingested_count} notes ({total_chunks} chunks).")

        # 3. Setup User B for Cross-User Isolation Evaluation
        email_b = f"benchmark_b_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "BenchmarkPassword456!",
            "full_name": "Benchmark User B (Isolation Check)"
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 4. Evaluate Retrieval (30 Queries)
        logger.info(f"Evaluating {len(EVAL_QUERIES)} retrieval queries on User A notes...")
        r_at_1_count = 0
        r_at_5_count = 0
        reciprocal_ranks = []
        query_results = []

        for q in EVAL_QUERIES:
            res = await client.post(
                "/api/v1/notes/search",
                params={"query": q["query"], "top_k": 5},
                headers=headers_a
            )
            data = res.json()
            retrieved = data.get("results", [])

            # Check matches
            first_match_rank = None
            for rank, item in enumerate(retrieved, start=1):
                text_lower = item["text_content"].lower()
                title_lower = item.get("note_title", "").lower()
                if any(kw in text_lower or kw in title_lower for kw in q["keywords"]):
                    if first_match_rank is None:
                        first_match_rank = rank

            if first_match_rank == 1:
                r_at_1_count += 1
            if first_match_rank is not None and first_match_rank <= 5:
                r_at_5_count += 1
                reciprocal_ranks.append(1.0 / first_match_rank)
            else:
                reciprocal_ranks.append(0.0)

            query_results.append({
                "query": q["query"],
                "subject": q["subject"],
                "first_match_rank": first_match_rank,
                "retrieved_count": len(retrieved)
            })

        recall_at_1 = r_at_1_count / len(EVAL_QUERIES)
        recall_at_5 = r_at_5_count / len(EVAL_QUERIES)
        mrr = sum(reciprocal_ranks) / len(EVAL_QUERIES)

        logger.info(f"Retrieval Results: Recall@1={recall_at_1:.2f} | Recall@5={recall_at_5:.2f} | MRR={mrr:.3f}")

        # 5. Evaluate Cross-User Isolation (10 Queries from User B targeting User A's data)
        logger.info("Evaluating Cross-User Privacy Isolation (10 Queries from User B)...")
        leakage_count = 0
        for q in EVAL_QUERIES[:10]:
            res = await client.post(
                "/api/v1/notes/search",
                params={"query": q["query"], "top_k": 5},
                headers=headers_b
            )
            data = res.json()
            retrieved = data.get("results", [])
            if len(retrieved) > 0:
                leakage_count += 1

        cross_user_leakage_rate = leakage_count / 10.0
        logger.info(f"Cross-User Leakage Rate: {cross_user_leakage_rate:.2%}")

        # 6. Evaluate Deterministic MCQ Scorer Reliability (15 trials)
        logger.info("Evaluating Deterministic MCQ Scorer Reliability...")
        # Create a test assessment
        goal_res = await client.post("/api/v1/goals", json={
            "subject": "Operating Systems",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers_a)
        lesson_id = goal_res.json()["modules"][0]["lessons"][0]["id"]

        quiz_res = await client.post(f"/api/v1/lessons/{lesson_id}/quiz", headers=headers_a)
        assert quiz_res.status_code == 200, f"Quiz generation failed: {quiz_res.text}"
        assessment_id = quiz_res.json()["assessment_id"]

        # Run 10 submissions with exact same MCQ choices
        sub_scores = []
        for trial in range(10):
            async with AsyncSessionLocal() as db:
                await db.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id == assessment_id))
                await db.commit()

            sub = await client.post(
                f"/api/v1/lessons/{lesson_id}/quiz/submit",
                json={
                    "assessment_id": assessment_id,
                    "answers": [
                        {"question_index": 0, "selected_option": "A"},
                        {"question_index": 1, "selected_option": "A"},
                        {"question_index": 2, "selected_option": "A"},
                        {"question_index": 3, "written_answer": ""}
                    ]
                },
                headers=headers_a
            )
            assert sub.status_code == 200, f"Submission failed with status {sub.status_code}: {sub.text}"
            sub_scores.append(sub.json()["mcq_score"])

        mcq_variance = max(sub_scores) - min(sub_scores)
        logger.info(f"Deterministic MCQ Scorer Variance across 10 trials: {mcq_variance:.4f}")

        # 7. Summary
        results = {
            "total_documents": len(BENCHMARK_CORPUS),
            "total_chunks_indexed": total_chunks,
            "total_eval_queries": len(EVAL_QUERIES),
            "recall_at_1": round(recall_at_1, 4),
            "recall_at_5": round(recall_at_5, 4),
            "mrr": round(mrr, 4),
            "cross_user_leakage_rate": round(cross_user_leakage_rate, 4),
            "deterministic_mcq_variance": round(mcq_variance, 4),
            "passed_gate": (recall_at_5 >= 0.80 and cross_user_leakage_rate == 0.0 and mcq_variance == 0.0)
        }

        # Save results
        out_file = Path("evals/results/phase2_metrics.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Phase 2 Benchmark completed. Metrics saved to {out_file}.")
        print("\n=== PHASE 2 BENCHMARK METRICS ===")
        print(json.dumps(results, indent=2))
        return results


if __name__ == "__main__":
    asyncio.run(run_benchmark())
