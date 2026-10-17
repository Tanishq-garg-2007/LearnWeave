"""Ownership-scoped loaders.

Every lesson belongs to a roadmap, and every roadmap belongs to exactly one user
(Roadmap.user_id). These helpers resolve resources only through that chain, so a
caller who knows a foreign UUID gets NotFoundError (HTTP 404) instead of the data.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Assessment, Lesson, Module, Roadmap, User
from app.services.errors import NotFoundError


async def get_owned_lesson(
    db: AsyncSession,
    lesson_id: str,
    user: User,
    *,
    load_module: bool = False,
    load_module_roadmap: bool = False,
) -> Lesson:
    """Return the lesson if it belongs to a roadmap owned by ``user``; otherwise NotFoundError."""
    stmt = (
        select(Lesson)
        .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
        .where(Lesson.id == lesson_id, Roadmap.user_id == user.id)
    )
    if load_module_roadmap:
        stmt = stmt.options(selectinload(Lesson.module).selectinload(Module.roadmap))
    elif load_module:
        stmt = stmt.options(selectinload(Lesson.module))

    res = await db.execute(stmt)
    lesson: Optional[Lesson] = res.scalar_one_or_none()
    if lesson is None:
        raise NotFoundError("Lesson not found")
    return lesson


async def get_owned_assessment(db: AsyncSession, assessment_id: str, user: User) -> Assessment:
    """Return the assessment if its lesson belongs to a roadmap owned by ``user``."""
    stmt = (
        select(Assessment)
        .join(Lesson, Assessment.lesson_id == Lesson.id)
        .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
        .where(Assessment.id == assessment_id, Roadmap.user_id == user.id)
    )
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if assessment is None:
        raise NotFoundError("Assessment not found")
    return assessment
