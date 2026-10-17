import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Assessment, AssessmentAttempt
from app.api.deps import get_current_user
from app.api.error_utils import internal_error, new_error_reference
from app.schemas.lessons import (
    LessonGenerateResponse, DoubtRequest, DoubtResponse,
    QuizResponse, QuizSubmitRequest, QuizSubmitResponse
)
from app.services.errors import NotFoundError, StepError
from app.services.ownership import get_owned_lesson
from app.services.lesson_agent import lesson_agent
from app.services.doubt_agent import doubt_agent
from app.services.quiz_agent import quiz_agent, build_quiz_response, QuizGenerationError
from app.services.evaluation_agent import evaluation_agent
from app.services.adaptive_agent import adaptive_agent

logger = logging.getLogger("learnweave.api.lessons")
from app.api.rate_limit import limit_by_ip, limit_by_user

router = APIRouter(prefix="/lessons", tags=["Lessons & Agentic Learning Cycle"])

RETRY_AFTER = "30"


def _unavailable(exc: BaseException, public_message: str) -> HTTPException:
    """503 with a reference id and Retry-After. Upstream and driver text stays in the server log."""
    err = internal_error(logger, exc, public_message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    err.headers = {"Retry-After": RETRY_AFTER}
    return err


def _from_step_error(exc: StepError) -> HTTPException:
    if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        ref = new_error_reference()
        logger.warning(f"[ref={ref}] {exc}")
        return HTTPException(
            status_code=exc.status_code,
            detail=f"{exc} (reference: {ref})",
            headers={"Retry-After": RETRY_AFTER},
        )
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{lesson_id}/generate", response_model=LessonGenerateResponse, dependencies=[Depends(limit_by_user('lesson_generate', 20, 60, llm=True))])
async def generate_lesson(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate or retrieve personalized lesson content.
    If student has uploaded relevant notes, uses Mode A (RAG-Grounded).
    If no notes match, uses Mode B (AI-Generated Learning).
    """
    try:
        # Returns cached content when present, otherwise generates it. Ownership is enforced.
        lesson, content, _cached = await lesson_agent.ensure_lesson_content(db=db, lesson_id=lesson_id, user=user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to generate lesson")

    return LessonGenerateResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        status=lesson.status,
        grounding_type=content.grounding_type,
        content=content
    )


@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve lesson metadata and any cached lesson content."""
    try:
        lesson = await get_owned_lesson(db, lesson_id, user, load_module=True)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return {
        "id": lesson.id,
        "title": lesson.title,
        "module_id": lesson.module_id,
        "module_title": lesson.module.title if lesson.module else None,
        "status": lesson.status,
        "duration_minutes": lesson.duration_minutes,
        "learning_objectives": lesson.learning_objectives or [],
        "lesson_content": lesson.lesson_content
    }


@router.post("/{lesson_id}/doubt", response_model=DoubtResponse, dependencies=[Depends(limit_by_user('doubt', 15, 60, llm=True))])
async def ask_doubt(
    lesson_id: str,
    req: DoubtRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a conceptual question or doubt regarding the lesson.
    Synthesizes answer from lesson content and student notes.
    """
    if not req.doubt or not req.doubt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doubt text cannot be empty"
        )

    try:
        response = await doubt_agent.resolve_doubt(
            db=db,
            lesson_id=lesson_id,
            doubt_text=req.doubt.strip(),
            user=user
        )
        return response
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to resolve doubt")


@router.get("/{lesson_id}/quiz", response_model=QuizResponse)
async def get_quiz(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Read the lesson's quiz. Read-only: it never calls the LLM (use POST to generate).
    Answer keys and ideal answers are never included.
    """
    try:
        assessment = await quiz_agent.get_current_assessment(db=db, lesson_id=lesson_id, user=user)
        return build_quiz_response(assessment)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StepError as exc:
        raise _from_step_error(exc)


@router.post("/{lesson_id}/quiz", response_model=QuizResponse, dependencies=[Depends(limit_by_user('quiz_gen', 10, 60, llm=True))])
async def create_or_get_quiz(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate the lesson's quiz if none exists yet, otherwise return the existing one. Idempotent."""
    try:
        assessment = await quiz_agent.generate_quiz(db=db, lesson_id=lesson_id, user=user)
        return build_quiz_response(assessment)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except QuizGenerationError as exc:
        raise _unavailable(exc, "Quiz generation is temporarily unavailable")
    except StepError as exc:
        raise _from_step_error(exc)
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to prepare quiz")


@router.post("/{lesson_id}/quiz/submit", response_model=QuizSubmitResponse, dependencies=[Depends(limit_by_user('quiz_submit', 20, 60, llm=True))])
async def submit_quiz(
    lesson_id: str,
    req: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit student answers for automated evaluation:
    - Deterministic MCQ scoring in Python.
    - Rubric-based evaluation for short-answer questions (503 if the grader is unavailable; nothing is recorded).
    - Mastery tracking and automatic lesson completion if score >= 70%.
    - A failed attempt triggers adaptive replanning; its result is returned in `adaptation`.
    """
    try:
        assessment = await quiz_agent.get_current_assessment(db=db, lesson_id=lesson_id, user=user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if req.assessment_id is not None and req.assessment_id != assessment.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This quiz has been replaced. Fetch the current quiz and submit again.",
        )

    try:
        result = await evaluation_agent.evaluate_submission(
            db=db,
            assessment_id=assessment.id,
            submission=req,
            user=user
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StepError as exc:
        raise _from_step_error(exc)
    except Exception as exc:
        raise internal_error(logger, exc, "Quiz evaluation failed")

    if not result.passed:
        try:
            result.adaptation = await adaptive_agent.adapt_after_assessment(
                db=db,
                lesson_id=lesson_id,
                overall_score=result.overall_score,
                passed=False,
                user=user,
            )
        except Exception:
            # The attempt is already saved. Report the replanning failure without a claim that it ran.
            await db.rollback()
            logger.exception("Adaptive replanning failed after a saved quiz attempt")
            result.adaptation = {
                "action": "unavailable",
                "message": "Your attempt was saved, but adaptive replanning could not run. Try again later.",
            }

    return result


@router.get("/{lesson_id}/attempts")
async def list_attempts(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List student's historical assessment attempts on this lesson."""
    try:
        await get_owned_lesson(db, lesson_id, user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    stmt = (
        select(AssessmentAttempt)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .where(
            Assessment.lesson_id == lesson_id,
            AssessmentAttempt.user_id == user.id
        )
        .order_by(AssessmentAttempt.created_at.desc())
    )
    res = await db.execute(stmt)
    attempts = res.scalars().all()

    return [
        {
            "id": a.id,
            "assessment_id": a.assessment_id,
            "score": a.score,
            "passed": a.passed,
            "feedback": a.feedback,
            "topic_mastery_impact": a.topic_mastery_impact,
            "created_at": a.created_at
        }
        for a in attempts
    ]
