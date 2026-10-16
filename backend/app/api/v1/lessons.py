import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import User, Lesson, Assessment, AssessmentAttempt
from app.api.deps import get_current_user
from app.schemas.lessons import (
    LessonContent, LessonGenerateResponse, DoubtRequest, DoubtResponse,
    QuizResponse, QuizQuestionItem, QuizSubmitRequest, QuizSubmitResponse
)
from app.services.lesson_agent import lesson_agent
from app.services.doubt_agent import doubt_agent
from app.services.quiz_agent import quiz_agent
from app.services.evaluation_agent import evaluation_agent

logger = logging.getLogger("learnweave.api.lessons")
router = APIRouter(prefix="/lessons", tags=["Lessons & Agentic Learning Cycle"])


@router.post("/{lesson_id}/generate", response_model=LessonGenerateResponse)
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
    res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    # If lesson content is already cached, return it
    if lesson.lesson_content and "sections" in lesson.lesson_content and lesson.lesson_content.get("sections"):
        content_dict = lesson.lesson_content
        content = LessonContent(**content_dict)
        return LessonGenerateResponse(
            lesson_id=lesson.id,
            title=lesson.title,
            status=lesson.status,
            grounding_type=content.grounding_type,
            content=content
        )

    # Generate lesson content
    try:
        content = await lesson_agent.generate_lesson(db=db, lesson_id=lesson_id, user=user)
        return LessonGenerateResponse(
            lesson_id=lesson.id,
            title=lesson.title,
            status=lesson.status,
            grounding_type=content.grounding_type,
            content=content
        )
    except Exception as exc:
        logger.error(f"Lesson generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lesson: {exc}"
        )


@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve lesson metadata and any cached lesson content."""
    res = await db.execute(
        select(Lesson).options(selectinload(Lesson.module)).where(Lesson.id == lesson_id)
    )
    lesson = res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

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


@router.post("/{lesson_id}/doubt", response_model=DoubtResponse)
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Doubt resolution error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resolve doubt")


@router.get("/{lesson_id}/quiz", response_model=QuizResponse)
async def get_or_generate_quiz(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve or generate formative assessment for the lesson.
    Sanitizes questions to hide answer keys from student payload.
    """
    try:
        assessment = await quiz_agent.generate_quiz(db=db, lesson_id=lesson_id, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Quiz generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to prepare quiz")

    # Sanitize questions: strip out correct_answer and ideal_answer
    sanitized_items = []
    for q in (assessment.questions or []):
        sanitized_items.append(QuizQuestionItem(
            question_index=q["question_index"],
            question_type=q["question_type"],
            question=q["question"],
            options=q.get("options"),
            rubric_criteria=q.get("rubric_criteria")
        ))

    return QuizResponse(
        assessment_id=assessment.id,
        lesson_id=assessment.lesson_id,
        title=assessment.title,
        questions=sanitized_items
    )


@router.post("/{lesson_id}/quiz/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    lesson_id: str,
    req: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit student answers for automated evaluation:
    - Deterministic MCQ scoring in Python.
    - Rubric-based evaluation for short-answer questions.
    - Mastery tracking and automatic lesson completion if score >= 70%.
    """
    res = await db.execute(select(Assessment).where(Assessment.lesson_id == lesson_id))
    assessment = res.scalars().first()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assessment exists for this lesson yet. Call GET /lessons/{id}/quiz first."
        )

    try:
        result = await evaluation_agent.evaluate_submission(
            db=db,
            assessment_id=assessment.id,
            submission=req,
            user=user
        )
        return result
    except Exception as exc:
        logger.error(f"Quiz submission evaluation error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Evaluation failed: {exc}")


@router.get("/{lesson_id}/attempts")
async def list_attempts(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List student's historical assessment attempts on this lesson."""
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
