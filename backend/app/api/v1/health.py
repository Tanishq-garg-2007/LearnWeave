from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db.session import get_db
from app.config import settings
from app.api.error_utils import new_error_reference

logger = logging.getLogger("learnweave.health")

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness check confirming ASGI server is running."""
    return {
        "status": "healthy",
        "service": "LearnWeave AI Backend",
        "version": "1.0.0"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking database connectivity and vector extension."""
    checks = {
        "database": False,
        "pgvector": False,
        "groq_configured": bool(settings.GROQ_API_KEY)
    }

    try:
        # Check database connection
        res = await db.execute(text("SELECT 1;"))
        if res.scalar() == 1:
            checks["database"] = True

        # Check pgvector extension
        vec_res = await db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';"))
        row = vec_res.scalar()
        if row is not None:
            checks["pgvector"] = True
    except Exception as exc:
        ref = new_error_reference()
        logger.error(f"[ref={ref}] Readiness check failed: {exc!r}")
        return {
            "status": "degraded",
            "checks": checks,
            "error": f"Readiness check failed (reference: {ref})"
        }

    all_ready = checks["database"] and checks["pgvector"]
    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks
    }
