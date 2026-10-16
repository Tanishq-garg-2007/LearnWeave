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
from app.services.wilson_service import calculate_wilson_score


def test_wilson_score_mathematical_properties():
    """Verify Wilson score confidence interval lower bound calculation."""
    # 0 votes -> 0.0
    assert calculate_wilson_score(0, 0) == 0.0

    # 10 upvotes, 0 downvotes vs 1 upvote, 0 downvotes
    w_10 = calculate_wilson_score(10, 0)
    w_1 = calculate_wilson_score(1, 0)
    assert w_10 > w_1, f"10 positive votes ({w_10}) must outrank 1 positive vote ({w_1})"
    assert w_10 >= 0.70
    assert w_1 <= 0.30

    # 100 upvotes, 5 downvotes vs 5 upvotes, 0 downvotes
    w_100_5 = calculate_wilson_score(100, 5)
    w_5_0 = calculate_wilson_score(5, 0)
    assert w_100_5 > w_5_0, f"100/105 ({w_100_5}) must outrank 5/5 ({w_5_0})"


@pytest.mark.asyncio
async def test_community_publish_vote_and_ranking():
    """Verify publishing notes to community, voting, and dynamic Wilson score sorting."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create author
        author_email = f"author_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": author_email,
            "password": "Password123!",
            "full_name": "Author Alice"
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Upload note as public
        content = "Distributed key-value store architecture using consistent hashing and virtual nodes."
        files = {"file": ("kv.txt", io.BytesIO(content.encode("utf-8")), "text/plain")}
        up_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Distributed Systems", "title": "Consistent Hashing Deep Dive", "visibility": "public"},
            files=files,
            headers=headers_a
        )
        assert up_res.status_code == 201
        note_id = up_res.json()["id"]

        # Register 3 distinct voters
        voter_tokens = []
        for i in range(3):
            v_reg = await client.post("/api/v1/auth/register", json={
                "email": f"voter_{i}_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Password123!",
                "full_name": f"Voter {i}"
            })
            voter_tokens.append(v_reg.json()["access_token"])

        # Voter 0 and 1 upvote
        for tok in voter_tokens[:2]:
            v_res = await client.post(
                f"/api/v1/community/notes/{note_id}/vote",
                json={"vote_value": 1},
                headers={"Authorization": f"Bearer {tok}"}
            )
            assert v_res.status_code == 200

        # Voter 2 downvotes
        down_res = await client.post(
            f"/api/v1/community/notes/{note_id}/vote",
            json={"vote_value": -1},
            headers={"Authorization": f"Bearer {voter_tokens[2]}"}
        )
        assert down_res.status_code == 200
        vote_data = down_res.json()
        assert vote_data["upvotes"] == 2
        assert vote_data["downvotes"] == 1
        assert vote_data["wilson_score"] > 0.0

        # Query community notes
        comm_res = await client.get("/api/v1/community/notes?subject=Distributed", headers=headers_a)
        assert comm_res.status_code == 200
        notes = comm_res.json()["notes"]
        assert any(n["id"] == note_id for n in notes)
        matched = [n for n in notes if n["id"] == note_id][0]
        assert matched["upvotes"] == 2
        assert matched["downvotes"] == 1


@pytest.mark.asyncio
async def test_independent_copy_import():
    """Verify that importing a community note creates an independent clone unaffected by original note deletion."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates and publishes note
        email_a = f"alice_pub_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "Alice"})
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        note_content = "PostgreSQL multi-version concurrency control (MVCC) uses transaction IDs (xmin, xmax) for row visibility."
        files = {"file": ("mvcc.md", io.BytesIO(note_content.encode("utf-8")), "text/markdown")}
        up_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "Database Internals", "title": "PostgreSQL MVCC Fundamentals", "visibility": "public"},
            files=files,
            headers=headers_a
        )
        note_id_a = up_res.json()["id"]

        # User B registers and imports User A's note
        email_b = f"bob_importer_{uuid.uuid4().hex[:6]}@example.com"
        reg_b = await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "Bob"})
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        import_res = await client.post(f"/api/v1/community/notes/{note_id_a}/import", headers=headers_b)
        assert import_res.status_code == 200
        imp_data = import_res.json()
        imported_note_id = imp_data["imported_note_id"]
        assert imported_note_id != note_id_a, "Imported note must have a new distinct UUID"
        assert imp_data["chunks_imported"] >= 1

        # User B can view their imported note in their private workspace
        bob_note = await client.get(f"/api/v1/notes/{imported_note_id}", headers=headers_b)
        assert bob_note.status_code == 200
        assert bob_note.json()["visibility"] == "private"
        assert len(bob_note.json()["chunks"]) >= 1

        # User A DELETES their original note
        del_res = await client.delete(f"/api/v1/notes/{note_id_a}", headers=headers_a)
        assert del_res.status_code == 200

        # Invariant Verification: User B's copy STILL EXISTS and is fully readable
        bob_copy_after = await client.get(f"/api/v1/notes/{imported_note_id}", headers=headers_b)
        assert bob_copy_after.status_code == 200, "Imported clone must survive deletion of original note!"
        assert "MVCC" in bob_copy_after.json()["title"] or "PostgreSQL" in bob_copy_after.json()["raw_content"]


@pytest.mark.asyncio
async def test_moderation_quarantine():
    """Verify that accumulating 3 reports automatically quarantines a note from the community library."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Author creates note
        email_a = f"bad_author_{uuid.uuid4().hex[:6]}@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "Bad Actor"})
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        files = {"file": ("spam.txt", io.BytesIO(b"Spam advertising and deceptive content."), "text/plain")}
        up_res = await client.post(
            "/api/v1/notes/upload",
            data={"subject": "General", "title": "Spam Note", "visibility": "public"},
            files=files,
            headers=headers_a
        )
        note_id = up_res.json()["id"]

        # Ensure note is in community list initially
        init_comm = await client.get("/api/v1/community/notes", headers=headers_a)
        assert any(n["id"] == note_id for n in init_comm.json()["notes"])

        # 3 distinct users report the note
        for i in range(3):
            reg_rep = await client.post("/api/v1/auth/register", json={
                "email": f"reporter_{i}_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Password123!",
                "full_name": f"Reporter {i}"
            })
            tok = reg_rep.json()["access_token"]
            rep_res = await client.post(
                f"/api/v1/community/notes/{note_id}/report",
                json={"reason": f"Violation of terms of service: deceptive content #{i}"},
                headers={"Authorization": f"Bearer {tok}"}
            )
            assert rep_res.status_code == 200

        # Note should now be automatically quarantined
        comm_after = await client.get("/api/v1/community/notes", headers=headers_a)
        assert not any(n["id"] == note_id for n in comm_after.json()["notes"]), "Quarantined note must NOT appear in community library"
