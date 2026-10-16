import asyncio
import sys
from pathlib import Path
import httpx

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app
from app.db.session import AsyncSessionLocal
from sqlalchemy import text


async def run_backend_smoke_tests():
    print("=" * 60)
    print("LEARNWEAVE AI — BACKEND & DATABASE SMOKE TEST RUNNER")
    print("=" * 60)

    # 1. Database & pgvector check via SQLAlchemy async session
    print("\n[1/3] Testing PostgreSQL Async Session & pgvector extension...")
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT 1;"))
            assert res.scalar() == 1, "SELECT 1 failed"

            ext_res = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
            ext_ver = ext_res.scalar()
            assert ext_ver is not None, "pgvector extension not found in database"
            print(f"  ✓ Database connected! pgvector version: {ext_ver}")

            # Test vector arithmetic directly in PostgreSQL
            vec_test = await session.execute(text("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector AS dist;"))
            dist = vec_test.scalar()
            print(f"  ✓ pgvector L2 distance calculation verified: dist={dist}")
    except Exception as exc:
        print(f"  ✗ Database check FAILED: {exc}")
        return False

    # 2. FastAPI ASGI endpoint test: /health
    print("\n[2/3] Testing FastAPI Liveness endpoint (/health)...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        print(f"  Status: {resp.status_code} | Body: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json().get("status") == "healthy"
        print("  ✓ /health endpoint: PASSED")

    # 3. FastAPI ASGI endpoint test: /api/v1/ready
    print("\n[3/3] Testing FastAPI Readiness endpoint (/api/v1/ready)...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ready")
        data = resp.json()
        print(f"  Status: {resp.status_code} | Body: {data}")
        assert resp.status_code == 200
        assert data.get("status") == "ready", f"Service not ready: {data}"
        assert data.get("checks", {}).get("database") is True
        assert data.get("checks", {}).get("pgvector") is True
        print("  ✓ /api/v1/ready endpoint: PASSED")

    print("\n" + "=" * 60)
    print("BACKEND SMOKE TEST SUMMARY: ALL PASSED!")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_backend_smoke_tests())
    sys.exit(0 if success else 1)
