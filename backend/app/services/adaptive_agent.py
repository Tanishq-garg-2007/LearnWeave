import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson, LearnerProfile, Roadmap, RoadmapVersion, StudySchedule, User
from app.services.learning_topics import REMEDIAL_KEY, topic_lesson_for
from app.services.ownership import get_owned_lesson

logger = logging.getLogger("learnweave.adaptive_agent")

REMEDIAL_PREFIX = "Targeted Revision: "
SESSION_HOUR_UTC = 18  # same slot the scheduler uses for lessons and reviews


def _next_session_time(now: Optional[datetime] = None) -> datetime:
    base = (now or datetime.utcnow()) + timedelta(days=1)
    return base.replace(hour=SESSION_HOUR_UTC, minute=0, second=0, microsecond=0)


class AdaptiveReplanningAgent:
    """
    Monitors learner mastery after assessments and performs adaptive roadmap adjustments:
    - If score < 70%: inserts ONE remedial revision lesson per topic (a repeat failure reuses the open one),
      bumps roadmap.version and roadmap_versions, and schedules the revision.
    - If score >= 70%: Completes lesson, updates topic mastery, and advances learner progression.
    """

    async def adapt_after_assessment(
        self,
        db: AsyncSession,
        lesson_id: str,
        overall_score: float,
        passed: bool,
        user: User
    ) -> Dict[str, Any]:
        # 1. Load lesson with module and roadmap, only if the user owns it
        lesson = await get_owned_lesson(db, lesson_id, user, load_module_roadmap=True)

        module = lesson.module
        roadmap = module.roadmap if module else None
        if not roadmap:
            raise ValueError(f"Roadmap not associated with lesson {lesson_id}")

        # Weak areas and mastery are keyed by the topic lesson, so a revision maps to the lesson it revises.
        topic = await topic_lesson_for(db, lesson)

        # 2. Load learner profile
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()
        score_pct = int(overall_score * 100)

        if passed:
            logger.info(f"Student passed {lesson.title} ({score_pct}%). Advancing progression.")
            lesson.status = "completed"

            if profile:
                completed = list(profile.completed_lessons or [])
                if lesson.id not in completed:
                    completed.append(lesson.id)
                profile.completed_lessons = completed

                weak = list(profile.weak_areas or [])
                weak = [w for w in weak if w not in (topic.title, lesson.title)]
                profile.weak_areas = weak

            await db.commit()
            return {
                "action": "completed",
                "message": f"Congratulations! You mastered {lesson.title} with {score_pct}%.",
                "remedial_required": False
            }

        # 3. Handle remediation when score < 70%
        logger.info(f"Remediation triggered for {topic.title} (Score: {score_pct}%). Adapting roadmap...")

        if profile:
            weak = list(profile.weak_areas or [])
            if topic.title not in weak:
                weak.append(topic.title)
            profile.weak_areas = weak

        # Lock the roadmap row. Two failures at once must not both insert a revision or claim the same version.
        await db.execute(select(Roadmap).where(Roadmap.id == roadmap.id).with_for_update())

        open_remedial = await self._open_remedial(db, topic)
        if open_remedial is not None:
            # Already queued and not yet completed: reuse it rather than stacking another copy.
            scheduled = await self._open_session(db, user.id, open_remedial.id)
            if scheduled is None:
                when = _next_session_time()
                db.add(StudySchedule(user_id=user.id, lesson_id=open_remedial.id, scheduled_date=when, status="pending"))
            else:
                when = scheduled.scheduled_date
            await db.commit()
            return {
                "action": "remedial_exists",
                "remedial_lesson_id": open_remedial.id,
                "remedial_lesson_title": open_remedial.title,
                "new_roadmap_version": roadmap.version,
                "scheduled_date": when.isoformat(),
                "message": f"'{open_remedial.title}' is already on your schedule. Review it before the next attempt."
            }

        return await self._insert_remedial(db, user, roadmap, topic, overall_score, score_pct)

    async def _open_remedial(self, db: AsyncSession, topic: Lesson) -> Optional[Lesson]:
        res = await db.execute(
            select(Lesson)
            .where(
                Lesson.roadmap_id == topic.roadmap_id,
                Lesson.status != "completed",
                Lesson.lesson_content[REMEDIAL_KEY].astext == topic.id,
            )
            .order_by(Lesson.created_at.asc(), Lesson.id.asc())
            .limit(1)
        )
        return res.scalars().first()

    async def _open_session(self, db: AsyncSession, user_id: str, lesson_id: str) -> Optional[StudySchedule]:
        res = await db.execute(
            select(StudySchedule)
            .where(
                StudySchedule.user_id == user_id,
                StudySchedule.lesson_id == lesson_id,
                StudySchedule.status.in_(["pending", "scheduled"]),
            )
            .order_by(StudySchedule.scheduled_date.asc())
            .limit(1)
        )
        return res.scalars().first()

    async def _insert_remedial(
        self,
        db: AsyncSession,
        user: User,
        roadmap: Roadmap,
        topic: Lesson,
        overall_score: float,
        score_pct: int,
    ) -> Dict[str, Any]:
        # Shift all subsequent lessons in the module down by 1
        later = await db.execute(
            select(Lesson).where(
                Lesson.module_id == topic.module_id,
                Lesson.order_index > topic.order_index,
            )
        )
        for l in later.scalars().all():
            l.order_index += 1

        remedial_lesson = Lesson(
            module_id=topic.module_id,
            roadmap_id=topic.roadmap_id,
            title=(REMEDIAL_PREFIX + topic.title)[:255],
            order_index=topic.order_index + 1,
            status="pending",
            duration_minutes=max(15, (topic.duration_minutes or 30) // 2),
            learning_objectives=[
                f"Reinforce core principles of {topic.title}",
                "Review tricky edge cases and common misconception traps"
            ],
            lesson_content={
                "is_revision": True,
                REMEDIAL_KEY: topic.id,
                "trigger_score": overall_score
            }
        )
        db.add(remedial_lesson)
        await db.flush()

        roadmap.total_lessons = (roadmap.total_lessons or 0) + 1

        v_res = await db.execute(
            select(func.coalesce(func.max(RoadmapVersion.version_number), 1))
            .where(RoadmapVersion.roadmap_id == roadmap.id)
        )
        new_version_num = max(int(v_res.scalar() or 1), int(roadmap.version or 1)) + 1
        roadmap.version = new_version_num

        reason = f"Remedial revision inserted after {score_pct}% score on '{topic.title}'"
        db.add(RoadmapVersion(
            roadmap_id=roadmap.id,
            version_number=new_version_num,
            change_reason=reason,
            snapshot_data={
                "version": new_version_num,
                "adapted_at": datetime.utcnow().isoformat(),
                "reason": reason,
                "inserted_lesson_id": remedial_lesson.id,
                "target_module_id": topic.module_id,
            },
        ))

        sched_time = _next_session_time()
        db.add(StudySchedule(
            user_id=user.id,
            lesson_id=remedial_lesson.id,
            scheduled_date=sched_time,
            status="pending",
        ))

        await db.commit()
        await db.refresh(remedial_lesson)

        return {
            "action": "remedial_inserted",
            "remedial_lesson_id": remedial_lesson.id,
            "remedial_lesson_title": remedial_lesson.title,
            "new_roadmap_version": new_version_num,
            "scheduled_date": sched_time.isoformat(),
            "message": f"Adaptive replanning activated: Added '{remedial_lesson.title}' to your active schedule to reinforce your understanding."
        }


adaptive_agent = AdaptiveReplanningAgent()
