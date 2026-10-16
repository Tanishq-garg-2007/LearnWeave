import sys
from pathlib import Path
import pytest
import pytest_asyncio
import httpx
from sqlalchemy import text

# Configure path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app
from app.db.session import AsyncSessionLocal
from app.services.roadmap_agent import roadmap_agent
from app.schemas.roadmaps import GoalCreateRequest, RoadmapGenerationOutput


@pytest.mark.asyncio
async def test_auth_and_private_workspace():
    """Test user registration, JWT generation, and private-by-default workspace isolation."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A
        email_a = "alice@example.com"
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "securepassword123",
            "full_name": "Alice Turing"
        })
        assert reg_a.status_code in (201, 400), f"Registration failed: {reg_a.text}"

        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "securepassword123"
        })
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]
        ws_a = login_a.json()["workspace_id"]
        assert ws_a, "Workspace ID missing"

        # 2. Register User B
        email_b = "bob@example.com"
        await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "securepassword456",
            "full_name": "Bob Hopper"
        })
        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "securepassword456"
        })
        assert login_b.status_code == 200
        ws_b = login_b.json()["workspace_id"]

        # Ensure workspaces are completely distinct (private by default)
        assert ws_a != ws_b, "Workspaces must be isolated between users"

        # 3. Test /me profile endpoint
        me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["email"] == email_a
        assert me_data["workspace_id"] == ws_a
        assert me_data["profile"]["preferences"]["learning_style"] == "practical"


@pytest.mark.asyncio
async def test_roadmap_agent_rules():
    """Test RoadmapPlanningAgent enforces 2-week active detailed window and placeholder modules."""
    goal = GoalCreateRequest(
        subject="Computer Systems Architecture",
        target_level="intermediate",
        current_level="beginner",
        total_duration_weeks=4,
        hours_per_week=5.0,
        preferred_style="hands-on diagrams and code",
        specific_objectives=["Understand CPU caches", "Memory hierarchies"]
    )

    plan: RoadmapGenerationOutput = await roadmap_agent.generate_roadmap(goal)

    assert plan.subject.lower() in ("computer systems architecture", "systems architecture") or len(plan.title) > 3
    assert len(plan.modules) >= 2, "Must generate at least 2 modules"

    # Verify 2-week active window rule
    for mod in plan.modules:
        if mod.target_week <= 2:
            assert not mod.is_planned_later, f"Week {mod.target_week} module must NOT be marked plan later"
            assert len(mod.lessons) >= 1, f"Week {mod.target_week} module must have detailed lessons"
            for les in mod.lessons:
                assert les.duration_minutes >= 15
                assert len(les.learning_objectives) >= 1
        else:
            assert mod.is_planned_later, f"Week {mod.target_week} module must be marked is_planned_later=true"


@pytest.mark.asyncio
async def test_goal_creation_and_roadmap_api():
    """Test API POST /api/v1/goals creates goal, generates roadmap, and links lessons."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login Alice
        login = await client.post("/api/v1/auth/login", json={
            "email": "alice@example.com",
            "password": "securepassword123"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Goal
        goal_payload = {
            "subject": "Data Structures & Algorithms",
            "target_level": "intermediate",
            "current_level": "beginner",
            "total_duration_weeks": 4,
            "hours_per_week": 6.0,
            "preferred_style": "visual analogies and step-by-step code",
            "specific_objectives": ["Master Binary Search", "Understand Recursion"]
        }
        res = await client.post("/api/v1/goals", json=goal_payload, headers=headers)
        assert res.status_code == 201, f"Goal creation failed: {res.text}"
        data = res.json()

        roadmap_id = data["id"]
        assert roadmap_id
        assert data["is_active"] is True
        assert len(data["modules"]) >= 2

        # Verify active roadmap query
        active_res = await client.get("/api/v1/roadmaps/active", headers=headers)
        assert active_res.status_code == 200
        assert active_res.json()["id"] == roadmap_id

        # Verify lesson status update
        first_lesson = data["modules"][0]["lessons"][0]
        lesson_id = first_lesson["id"]
        status_res = await client.put(
            f"/api/v1/roadmaps/lessons/{lesson_id}/status",
            json={"new_status": "in_progress"},
            headers=headers
        )
        assert status_res.status_code == 200
        assert status_res.json()["current_status"] == "in_progress"
