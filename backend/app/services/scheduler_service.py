import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.models import StudySchedule, Lesson, Module, Roadmap, LearnerProfile, User

logger = logging.getLogger("learnweave.scheduler")


class StudySchedulerService:
    """
    Schedules active sprint study sessions and spaced repetition reviews.
    Adapts pacing to learner's daily_minutes capacity and schedules reviews for weak areas.
    """

    async def generate_sprint_schedule(
        self,
        db: AsyncSession,
        user: User,
        roadmap_id: str
    ) -> List[StudySchedule]:
        # 1. Fetch active roadmap lessons
        res = await db.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Module.roadmap_id == roadmap_id,
                Module.is_planned_later == False
            )
            .order_by(Module.order_index, Lesson.order_index)
        )
        lessons = res.scalars().all()
        if not lessons:
            return []

        # 2. Learner profile preferences
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()
        prefs = profile.preferences if profile and profile.preferences else {}
        daily_mins = prefs.get("daily_minutes", 45)

        # 3. Clear any existing pending schedule for this roadmap
        existing_res = await db.execute(
            select(StudySchedule).where(
                and_(
                    StudySchedule.user_id == user.id,
                    StudySchedule.status == "scheduled"
                )
            )
        )
        for item in existing_res.scalars().all():
            await db.delete(item)

        # 4. Lay out lessons over consecutive study days
        created_schedules = []
        current_date = datetime.utcnow().date() + timedelta(days=1)
        current_day_minutes = 0

        for lesson in lessons:
            dur = lesson.duration_minutes or 30
            if current_day_minutes + dur > daily_mins and current_day_minutes > 0:
                current_date += timedelta(days=1)
                current_day_minutes = 0

            sched = StudySchedule(
                user_id=user.id,
                lesson_id=lesson.id,
                scheduled_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=18),
                status="scheduled"
            )
            db.add(sched)
            created_schedules.append(sched)
            current_day_minutes += dur

        # 5. Check if profile has weak areas needing spaced repetition reviews
        if profile and profile.weak_areas:
            for weak_topic in profile.weak_areas[:3]:
                # Find lesson for weak topic
                w_res = await db.execute(
                    select(Lesson).where(
                        Lesson.roadmap_id == roadmap_id,
                        Lesson.title.ilike(f"%{weak_topic}%")
                    )
                )
                w_lesson = w_res.scalars().first()
                if w_lesson:
                    # Schedule review at +3 days and +7 days
                    for offset in (3, 7):
                        r_date = datetime.utcnow() + timedelta(days=offset)
                        rev_sched = StudySchedule(
                            user_id=user.id,
                            lesson_id=w_lesson.id,
                            scheduled_date=r_date,
                            status="scheduled"
                        )
                        db.add(rev_sched)
                        created_schedules.append(rev_sched)

        await db.commit()
        return created_schedules

    async def get_schedule(
        self,
        db: AsyncSession,
        user_id: str,
        upcoming_only: bool = False
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(StudySchedule, Lesson.title, Lesson.lesson_content)
            .outerjoin(Lesson, StudySchedule.lesson_id == Lesson.id)
            .where(StudySchedule.user_id == user_id)
            .order_by(StudySchedule.scheduled_date.asc())
        )
        if upcoming_only:
            stmt = stmt.where(StudySchedule.status == "scheduled")

        res = await db.execute(stmt)
        rows = res.all()

        output = []
        for s, l_title, l_content in rows:
            lesson_title = l_title or "General Study Session"
            is_rev = False
            if l_content:
                is_rev = l_content.get("is_revision", False)

            output.append({
                "id": s.id,
                "lesson_id": s.lesson_id,
                "lesson_title": lesson_title,
                "scheduled_date": s.scheduled_date.isoformat(),
                "status": s.status,
                "is_revision": is_rev
            })
        return output

    async def update_status(
        self,
        db: AsyncSession,
        schedule_id: str,
        new_status: str,
        user_id: str
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(StudySchedule).where(
                StudySchedule.id == schedule_id,
                StudySchedule.user_id == user_id
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError(f"Schedule item {schedule_id} not found")

        item.status = new_status
        await db.commit()
        return {"id": item.id, "status": item.status}


scheduler_service = StudySchedulerService()
