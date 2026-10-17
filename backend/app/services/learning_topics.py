"""Topic keys for mastery and weak areas.

profile.topic_mastery and profile.weak_areas are keyed by the lesson title (the frontend and the
scheduler read them as display strings). A remedial "Targeted Revision" lesson is not a topic of
its own: it revises another lesson, so its results count towards that lesson's topic.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson

REMEDIAL_KEY = "remedial_for_lesson_id"


def remedial_source_id(lesson: Lesson) -> Optional[str]:
    """The id of the lesson a remedial revision revises, or None for a regular lesson."""
    content = lesson.lesson_content if isinstance(lesson.lesson_content, dict) else {}
    source = content.get(REMEDIAL_KEY)
    return source if isinstance(source, str) and source else None


async def topic_lesson_for(db: AsyncSession, lesson: Lesson) -> Lesson:
    """Return the lesson whose title keys mastery and weak areas.

    The caller must already have verified that the user owns ``lesson``. The source lesson must be in
    the same roadmap, so ownership carries over.
    """
    source_id = remedial_source_id(lesson)
    if source_id is None:
        return lesson
    res = await db.execute(
        select(Lesson).where(Lesson.id == source_id, Lesson.roadmap_id == lesson.roadmap_id)
    )
    return res.scalar_one_or_none() or lesson
