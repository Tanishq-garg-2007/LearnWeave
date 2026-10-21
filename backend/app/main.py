import asyncio
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
from app.api.error_utils import new_error_reference

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("learnweave.main")


def _is_dev_env() -> bool:
    return settings.APP_ENV.strip().lower() == "development"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing LearnWeave AI backend service...")
    if not settings.GROQ_API_KEY:
        msg = "GROQ_API_KEY is not set. All AI features (lessons, quizzes, doubts, roadmaps, STT) will return errors."
        if not _is_dev_env():
            raise RuntimeError(msg)
        logger.warning(msg)
    else:
        logger.info(f"Groq primary model: {settings.GROQ_PRIMARY_MODEL} | Fallback: {settings.GROQ_FALLBACK_MODEL}")

    # Warm up Kokoro neural speech engine in background
    from app.services.tts_service import tts_service
    asyncio.create_task(asyncio.to_thread(tts_service.initialize_kokoro))

    yield
    logger.info("Shutting down LearnWeave AI backend...")


# API docs are published only in development; they describe the full API surface to anyone.
_is_dev = settings.APP_ENV.strip().lower() == "development"

app = FastAPI(
    title="LearnWeave AI — Agentic Learning Platform",
    description="Adaptive, personalized, privacy-conscious long-term learning companion.",
    version="1.0.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Exception handlers
@app.exception_handler(GroqClientError)
async def groq_exception_handler(request: Request, exc: GroqClientError):
    # Upstream response bodies stay in the log; clients get a generic message and a reference id.
    ref = new_error_reference()
    logger.error(f"[ref={ref}] Groq error (upstream status={exc.status_code}, retryable={exc.retryable}): {exc}")
    return JSONResponse(
        status_code=503 if exc.retryable else 502,
        content={
            "detail": f"The AI service is temporarily unavailable. Please try again. (reference: {ref})",
            "retryable": exc.retryable,
        }
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
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope
from starlette.responses import Response

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404 and self.html and not path.startswith("api/") and not path.startswith("assets/"):
                return await super().get_response("index.html", scope)
            raise ex

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")


