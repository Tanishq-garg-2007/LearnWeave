"""Single place that changes a lesson's status and keeps profile + schedule in step (BUG-25)."""
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson, LearnerProfile, StudySchedule
from app.services.errors import StepError


class LessonStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


LESSON_STATUSES = tuple(s.value for s in LessonStatus)
LEGACY_ALIASES = {"not_started": "pending", "scheduled": "pending"}


def normalize_status(raw: str) -> str:
    raw = LEGACY_ALIASES.get(raw, raw)
    if raw not in LESSON_STATUSES:
        raise StepError("Invalid lesson status", status_code=422)
    return raw


async def set_lesson_status(db: AsyncSession, user_id: str, lesson: Lesson, new_status: str) -> str:
    """Update lesson, learner profile and study sessions together. Does not commit."""
    new_status = normalize_status(new_status)
    lesson.status = new_status

    res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile: Optional[LearnerProfile] = res.scalar_one_or_none()
    if profile is not None:
        completed = list(profile.completed_lessons or [])
        if new_status == "completed" and lesson.id not in completed:
            completed.append(lesson.id)
        elif new_status != "completed" and lesson.id in completed:
            completed.remove(lesson.id)
        profile.completed_lessons = completed

    sess = await db.execute(
        select(StudySchedule).where(StudySchedule.user_id == user_id, StudySchedule.lesson_id == lesson.id)
    )
    for row in sess.scalars().all():
        if new_status in ("completed", "skipped"):
            row.status = new_status
        elif row.status in ("completed", "skipped"):
            row.status = "pending"
    return new_status
