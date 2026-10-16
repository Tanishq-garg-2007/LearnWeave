import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.goals import router as goals_router
from app.api.v1.roadmaps import router as roadmaps_router
from app.api.v1.notes import router as notes_router
from app.api.v1.lessons import router as lessons_router
from app.api.v1.voice import router as voice_router
from app.api.v1.cycle import router as cycle_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.community import router as community_router
from app.services.groq_client import GroqClientError

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("learnweave.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing LearnWeave AI backend service...")
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set. External AI features will run in mock/degraded mode.")
    else:
        logger.info(f"Groq primary model: {settings.GROQ_PRIMARY_MODEL} | Fallback: {settings.GROQ_FALLBACK_MODEL}")
    yield
    logger.info("Shutting down LearnWeave AI backend...")


app = FastAPI(
    title="LearnWeave AI — Agentic Learning Platform",
    description="Adaptive, personalized, privacy-conscious long-term learning companion.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(GroqClientError)
async def groq_exception_handler(request: Request, exc: GroqClientError):
    return JSONResponse(
        status_code=exc.status_code or 503,
        content={"detail": str(exc), "retryable": exc.retryable}
    )

@app.get("/health", tags=["Health"])
async def root_health():
    return {"status": "ok", "service": "LearnWeave AI"}

@app.get("/ready", tags=["Health"])
async def root_ready():
    from app.db.session import AsyncSessionLocal
    from app.api.v1.health import readiness
    async with AsyncSessionLocal() as session:
        return await readiness(session)

# Mount API v1 routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(roadmaps_router, prefix="/api/v1")
app.include_router(notes_router, prefix="/api/v1")
app.include_router(lessons_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(cycle_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(community_router, prefix="/api/v1")

# Mount frontend production build if available
from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

