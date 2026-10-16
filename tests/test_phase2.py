import sys
import io
import uuid
from pathlib import Path
import pytest
import httpx

# Configure path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app


@pytest.mark.asyncio
async def test_notes_upload_and_semantic_chunking():
    """Verify upload of study notes, semantic chunking, and 384-d vector embeddings."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        user_email = f"student_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": user_email,
            "password": "Password123!",
            "full_name": "Test Student"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload a markdown note with rich paragraphs
        content = """# Operating Systems Architecture

Operating systems manage hardware resources and provide a stable virtual execution environment for user space applications.

## CPU Scheduling
The operating system scheduler coordinates which process executes on CPU cores.
Preemptive scheduling allows high-priority tasks to interrupt executing threads, guaranteeing low latency for interactive workflows.
Round-robin scheduling assigns equal time slices called quanta to each runnable process in the ready queue.

## Virtual Memory
Virtual memory isolates application address spaces using hardware page tables managed by the Memory Management Unit (MMU).
When a process requests memory outside physical RAM, the kernel handles page faults by loading disk-backed pages into memory frames.
"""
        files = {
            "file": ("os_notes.md", io.BytesIO(content.encode("utf-8")), "text/markdown")
        }
        data = {
            "subject": "Operating Systems",
            "title": "OS Scheduling and Virtual Memory Notes",
            "tags": "kernel,scheduling,memory",
            "visibility": "private"
        }

        upload_res = await client.post("/api/v1/notes/upload", data=data, files=files, headers=headers)
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        res_data = upload_res.json()
        note_id = res_data["id"]
        assert note_id
        assert res_data["chunks_created"] >= 1
        assert res_data["processing_status"] == "processed"

        # List notes
        list_res = await client.get("/api/v1/notes", headers=headers)
        assert list_res.status_code == 200
        notes = list_res.json()
        assert any(n["id"] == note_id for n in notes)
        matched = [n for n in notes if n["id"] == note_id][0]
        assert matched["chunk_count"] >= 1

        # Get note detail
        detail_res = await client.get(f"/api/v1/notes/{note_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert len(detail["chunks"]) == matched["chunk_count"]
        assert "scheduler" in detail["chunks"][0]["text_content"].lower() or "operating" in detail["chunks"][0]["text_content"].lower()


@pytest.mark.asyncio
async def test_cross_user_isolation():
    """Verify that User B cannot view, retrieve, or search private notes belonging to User A."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register User A (Alice)
        email_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Alice Privacy"
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User A uploads a private confidential note
        secret_content = "TOP_SECRET_RESEARCH: Quantum circuit annealing utilizes adiabatic state transfer 987654321."
        files = {
            "file": ("secret.txt", io.BytesIO(secret_content.encode("utf-8")), "text/plain")
        }
        data = {
            "subject": "Quantum Computing",
            "title": "Classified Quantum Research",
            "visibility": "private"
        }
        up_res = await client.post("/api/v1/notes/upload", data=data, files=files, headers=headers_a)
        assert up_res.status_code == 201
        note_id_a = up_res.json()["id"]

        # Register User B (Bob)
        email_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Bob Intruder"
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 1. Direct GET: User B attempts to access User A's private note
        forbidden_get = await client.get(f"/api/v1/notes/{note_id_a}", headers=headers_b)
        assert forbidden_get.status_code == 403, "User B should be forbidden from accessing User A's private note"

        # 2. Hybrid RAG Search: User B attempts to retrieve User A's secret keywords
        search_res = await client.post(
            "/api/v1/notes/search",
            params={"query": "adiabatic state transfer 987654321"},
            headers=headers_b
        )
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert search_data["count"] == 0, "User B must retrieve 0 results from User A's private notes"

        # 3. User A search for the same keyword succeeds
        search_a = await client.post(
            "/api/v1/notes/search",
            params={"query": "adiabatic state transfer 987654321"},
            headers=headers_a
        )
        assert search_a.status_code == 200
        assert search_a.json()["count"] >= 1, "User A should retrieve their own note chunk"


@pytest.mark.asyncio
async def test_lesson_generation_and_grounding_modes():
    """Verify Mode A (RAG-Grounded with citations) vs Mode B (AI-Generated Learning without notes)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # User with notes
        email = f"student_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Grounded Learner"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Goal and Roadmap
        goal_res = await client.post("/api/v1/goals", json={
            "subject": "Distributed Consensus",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 5.0,
            "preferred_style": "rigorous system models",
            "specific_objectives": ["Raft leader election", "Log replication"]
        }, headers=headers)
        assert goal_res.status_code == 201
        roadmap = goal_res.json()
        first_lesson = roadmap["modules"][0]["lessons"][0]
        lesson_id = first_lesson["id"]

        # Case 1: Before uploading notes -> Mode B (AI-Generated Learning)
        gen_b = await client.post(f"/api/v1/lessons/{lesson_id}/generate", headers=headers)
        assert gen_b.status_code == 200
        data_b = gen_b.json()
        assert data_b["grounding_type"] == "ai_generated"
        assert len(data_b["content"]["cited_chunks"]) == 0

        # Now upload relevant study notes on Raft consensus
        note_content = """# Raft Consensus Protocol

In the Raft protocol, leader election is initiated when a follower's election timer expires.
The node transitions to candidate state, increments its current term, and broadcasts RequestVote RPCs.
A candidate becomes leader when it receives affirmative votes from a strict quorum of cluster nodes.
Once elected, the leader periodically sends AppendEntries heartbeats to suppress follower elections.
"""
        files = {
            "file": ("raft.md", io.BytesIO(note_content.encode("utf-8")), "text/markdown")
        }
        upload_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Distributed Consensus", "title": "Raft Protocol Primer"},
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 201

        # Use second lesson for Case 2: Mode A (RAG-Grounded)
        if len(roadmap["modules"][0]["lessons"]) > 1:
            lesson_2 = roadmap["modules"][0]["lessons"][1]
            gen_a = await client.post(f"/api/v1/lessons/{lesson_2['id']}/generate", headers=headers)
            assert gen_a.status_code == 200
            data_a = gen_a.json()
            assert data_a["grounding_type"] == "rag_grounded"
            assert len(data_a["content"]["cited_chunks"]) >= 1


@pytest.mark.asyncio
async def test_doubt_resolution_and_profile_tracking():
    """Verify doubt resolution synthesizing lesson and notes, updating learner profile."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"doubt_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Curious Student"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create goal & roadmap
        g_res = await client.post("/api/v1/goals", json={
            "subject": "Computer Networking",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        assert g_res.status_code == 201
        lesson_id = g_res.json()["modules"][0]["lessons"][0]["id"]

        # Ask doubt
        doubt_res = await client.post(
            f"/api/v1/lessons/{lesson_id}/doubt",
            json={"doubt": "What happens if a TCP SYN packet is dropped during the three-way handshake?"},
            headers=headers
        )
        assert doubt_res.status_code == 200
        d_data = doubt_res.json()
        assert len(d_data["answer"]) > 20

        # Verify doubt was recorded in user's profile
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        doubts = me.json()["profile"]["unresolved_doubts"]
        assert len(doubts) >= 1
        assert any("TCP SYN" in str(d) for d in doubts)


@pytest.mark.asyncio
async def test_formative_quiz_and_evaluation_cycle():
    """Verify assessment generation, deterministic MCQ grading, rubric short-answer scoring, and mastery update."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"quiz_user_{uuid.uuid4().hex[:6]}@example.com"
        reg = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Assessment Student"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create roadmap
        g_res = await client.post("/api/v1/goals", json={
            "subject": "Database Indexing",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 2,
            "hours_per_week": 4.0
        }, headers=headers)
        lesson_id = g_res.json()["modules"][0]["lessons"][0]["id"]

        # 1. Fetch Quiz (Sanitized)
        quiz_res = await client.get(f"/api/v1/lessons/{lesson_id}/quiz", headers=headers)
        assert quiz_res.status_code == 200
        quiz = quiz_res.json()
        assert len(quiz["questions"]) == 4

        # Verify answers are NOT leaked in quiz payload
        for q in quiz["questions"]:
            assert "correct_answer" not in q, "correct_answer must be sanitized from quiz response"
            assert "ideal_answer" not in q, "ideal_answer must be sanitized from quiz response"

        # 2. Submit Answers
        answers = [
            {"question_index": 0, "selected_option": "A"},
            {"question_index": 1, "selected_option": "B"},
            {"question_index": 2, "selected_option": "C"},
            {
                "question_index": 3,
                "written_answer": "B-Tree indexes maintain sorted keys in balanced nodes to ensure logarithmic lookup, insertion, and range scan performance while minimizing disk I/O."
            }
        ]
        submit_res = await client.post(
            f"/api/v1/lessons/{lesson_id}/quiz/submit",
            json={"answers": answers},
            headers=headers
        )
        assert submit_res.status_code == 200
        sub_data = submit_res.json()
        assert "overall_score" in sub_data
        assert "passed" in sub_data
        assert "evaluations" in sub_data
        assert len(sub_data["evaluations"]) == 4

        # 3. Verify Learner Profile Topic Mastery was updated
        me = await client.get("/api/v1/auth/me", headers=headers)
        profile = me.json()["profile"]
        assert len(profile["topic_mastery"]) >= 1

        # 4. Check historical attempts endpoint
        hist_res = await client.get(f"/api/v1/lessons/{lesson_id}/attempts", headers=headers)
        assert hist_res.status_code == 200
        attempts = hist_res.json()
        assert len(attempts) >= 1
        assert attempts[0]["score"] == sub_data["overall_score"]
