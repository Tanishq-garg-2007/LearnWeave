import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.db.models import Lesson, Module, Roadmap, RoadmapVersion, LearnerProfile, StudySchedule, User

logger = logging.getLogger("learnweave.adaptive_agent")


class AdaptiveReplanningAgent:
    """
    Monitors learner mastery after assessments and performs adaptive roadmap adjustments:
    - If score < 70%: Dynamically inserts remedial revision lesson, increments version in roadmap_versions, and reschedules study.
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
        # 1. Load lesson with module and roadmap
        res = await db.execute(
            select(Lesson)
            .options(selectinload(Lesson.module).selectinload(Module.roadmap))
            .where(Lesson.id == lesson_id)
        )
        lesson = res.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")

        module = lesson.module
        roadmap = module.roadmap if module else None
        if not roadmap:
            raise ValueError(f"Roadmap not associated with lesson {lesson_id}")

        # 2. Load learner profile
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()

        if passed:
            logger.info(f"Student passed {lesson.title} ({int(overall_score * 100)}%). Advancing progression.")
            lesson.status = "completed"

            if profile:
                completed = list(profile.completed_lessons or [])
                if lesson.id not in completed:
                    completed.append(lesson.id)
                profile.completed_lessons = completed

                weak = list(profile.weak_areas or [])
                if lesson.title in weak:
                    weak.remove(lesson.title)
                profile.weak_areas = weak

            await db.commit()
            return {
                "action": "completed",
                "message": f"Congratulations! You mastered {lesson.title} with {int(overall_score * 100)}%.",
                "remedial_required": False
            }

        # 3. Handle remediation when score < 70%
        logger.info(f"Remediation triggered for {lesson.title} (Score: {int(overall_score * 100)}%). Adapting roadmap...")

        # Record weak area in profile
        if profile:
            weak = list(profile.weak_areas or [])
            if lesson.title not in weak:
                weak.append(lesson.title)
            profile.weak_areas = weak

        # Shift all subsequent lessons in the module down by 1
        all_lessons_res = await db.execute(
            select(Lesson)
            .where(Lesson.module_id == module.id)
            .order_by(Lesson.order_index)
        )
        all_lessons = all_lessons_res.scalars().all()

        for l in all_lessons:
            if l.order_index > lesson.order_index:
                l.order_index += 1

        # Create the remedial lesson
        remedial_lesson = Lesson(
            module_id=module.id,
            roadmap_id=roadmap.id,
            title=f"Targeted Revision: {lesson.title}",
            order_index=lesson.order_index + 1,
            status="not_started",
            duration_minutes=max(15, (lesson.duration_minutes or 30) // 2),
            learning_objectives=[
                f"Reinforce core principles of {lesson.title}",
                "Review tricky edge cases and common misconception traps"
            ],
            lesson_content={
                "is_revision": True,
                "remedial_for_lesson_id": lesson.id,
                "trigger_score": overall_score
            }
        )
        db.add(remedial_lesson)
        await db.flush()

        # Update roadmap total_lessons counter
        roadmap.total_lessons = (roadmap.total_lessons or 0) + 1

        # Get latest version number
        v_res = await db.execute(
            select(func.coalesce(func.max(RoadmapVersion.version_number), 1))
            .where(RoadmapVersion.roadmap_id == roadmap.id)
        )
        latest_version = v_res.scalar() or 1
        new_version_num = latest_version + 1

        # Create new version snapshot in roadmap_versions
        snapshot = {
            "version": new_version_num,
            "adapted_at": datetime.utcnow().isoformat(),
            "reason": f"Remedial revision inserted after {int(overall_score * 100)}% score on '{lesson.title}'",
            "inserted_lesson_id": remedial_lesson.id,
            "target_module": module.title
        }

        version_record = RoadmapVersion(
            roadmap_id=roadmap.id,
            version_number=new_version_num,
            change_reason=snapshot["reason"],
            snapshot_data=snapshot
        )
        db.add(version_record)

        # Schedule remedial session tomorrow
        sched_time = datetime.utcnow() + timedelta(days=1)
        schedule_item = StudySchedule(
            user_id=user.id,
            lesson_id=remedial_lesson.id,
            scheduled_date=sched_time,
            status="scheduled"
        )
        db.add(schedule_item)

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
