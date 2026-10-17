import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerProfile, Lesson, Module, Roadmap, StudySchedule, User
from app.services.errors import NotFoundError, StepError

logger = logging.getLogger("learnweave.scheduler")

# Session statuses the API exposes (docs/api-contract-round2.md, ScheduleStatus in the frontend).
SESSION_STATUSES = ("pending", "completed", "skipped")
# "scheduled" is what rows written before round 2, and the adaptive remedial insert, carry.
# It counts as open and is reported to clients as "pending".
LEGACY_OPEN_STATUS = "scheduled"
OPEN_SESSION_STATUSES = ("pending", LEGACY_OPEN_STATUS)
# Lessons in these states are never scheduled again.
FINISHED_LESSON_STATUSES = ("completed", "skipped")

STUDY_TIME_UTC = time(hour=18)
DEFAULT_DAILY_MINUTES = 45
DEFAULT_LESSON_MINUTES = 30
MAX_REVIEW_TOPICS = 3
REVIEW_OFFSETS_DAYS = (3, 7)


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _study_slot(day: date) -> datetime:
    """Lesson and review sessions all sit on the same 18:00 UTC slot."""
    return datetime.combine(day, STUDY_TIME_UTC)


def _daily_minutes(profile: Optional[LearnerProfile]) -> int:
    prefs = profile.preferences if profile and isinstance(profile.preferences, dict) else {}
    try:
        minutes = int(prefs.get("daily_minutes", DEFAULT_DAILY_MINUTES))
    except (TypeError, ValueError):
        return DEFAULT_DAILY_MINUTES
    return minutes if minutes > 0 else DEFAULT_DAILY_MINUTES


def _review_topics(profile: Optional[LearnerProfile]) -> List[str]:
    """Weak topics exactly as stored (they are lesson titles), weakest first, capped."""
    if not profile or not isinstance(profile.weak_areas, list):
        return []
    topics = list(dict.fromkeys(t for t in profile.weak_areas if isinstance(t, str) and t.strip()))
    mastery = profile.topic_mastery if isinstance(profile.topic_mastery, dict) else {}

    def _score(topic: str) -> float:
        try:
            return float(mastery.get(topic, 0.0))
        except (TypeError, ValueError):
            return 0.0

    # sorted() is stable, so topics with equal mastery keep the order they were flagged in.
    return sorted(topics, key=_score)[:MAX_REVIEW_TOPICS]


def _public_status(raw: str) -> str:
    return "pending" if raw == LEGACY_OPEN_STATUS else raw


def _session_dict(session: StudySchedule, lesson_title: str, lesson_content: Any) -> Dict[str, Any]:
    is_revision = bool(lesson_content.get("is_revision", False)) if isinstance(lesson_content, dict) else False
    return {
        "id": session.id,
        "lesson_id": session.lesson_id,
        "lesson_title": lesson_title,
        "scheduled_date": session.scheduled_date.isoformat(),
        "status": _public_status(session.status),
        "is_revision": is_revision,
    }


def _add_session(db: AsyncSession, user_id: str, lesson_id: str, when: datetime) -> StudySchedule:
    session = StudySchedule(user_id=user_id, lesson_id=lesson_id, scheduled_date=when, status="pending")
    db.add(session)
    return session


class StudySchedulerService:
    """
    Schedules active sprint study sessions and spaced repetition reviews.
    Adapts pacing to learner's daily_minutes capacity and schedules reviews for weak areas.
    """

    async def generate_sprint_schedule(
        self,
        db: AsyncSession,
        user: User,
        roadmap_id: str,
        *,
        commit: bool = True,
    ) -> List[StudySchedule]:
        # 1. The roadmap must belong to the caller and be the active one. Checked before any write.
        roadmap = await self._get_owned_active_roadmap(db, user.id, roadmap_id)
        profile = await self._profile(db, user.id)

        # 2. Replace only this roadmap's open sessions. Other roadmaps and completed/skipped history stay.
        await db.execute(
            delete(StudySchedule)
            .where(
                StudySchedule.user_id == user.id,
                StudySchedule.status.in_(OPEN_SESSION_STATUSES),
                StudySchedule.lesson_id.in_(select(Lesson.id).where(Lesson.roadmap_id == roadmap.id)),
            )
            .execution_options(synchronize_session=False)
        )

        today = _utc_today()
        created: List[StudySchedule] = []

        # 3. Pack pending lessons into consecutive study days, starting tomorrow, within daily_minutes.
        daily_minutes = _daily_minutes(profile)
        day = today + timedelta(days=1)
        used_minutes = 0
        for lesson in await self._pending_lessons(db, roadmap.id):
            minutes = lesson.duration_minutes or DEFAULT_LESSON_MINUTES
            if used_minutes + minutes > daily_minutes and used_minutes > 0:
                day += timedelta(days=1)
                used_minutes = 0
            created.append(_add_session(db, user.id, lesson.id, _study_slot(day)))
            used_minutes += minutes

        # 4. Spaced repetition: reviews for weak topics at +3 and +7 days, on the same study slot.
        for topic in _review_topics(profile):
            lesson = await self._lesson_by_title(db, roadmap.id, topic)
            if lesson is None:
                continue
            for offset in REVIEW_OFFSETS_DAYS:
                created.append(_add_session(db, user.id, lesson.id, _study_slot(today + timedelta(days=offset))))

        if commit:
            await db.commit()
        return created

    async def drop_pending_sessions_except(
        self,
        db: AsyncSession,
        user_id: str,
        keep_roadmap_id: str,
    ) -> None:
        """Called when a roadmap becomes active. Removes the user's open sessions for every other roadmap.
        Completed and skipped sessions stay as history. Does not commit."""
        other_lessons = (
            select(Lesson.id)
            .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
            .where(Roadmap.user_id == user_id, Roadmap.id != keep_roadmap_id)
        )
        await db.execute(
            delete(StudySchedule)
            .where(
                StudySchedule.user_id == user_id,
                StudySchedule.status.in_(OPEN_SESSION_STATUSES),
                StudySchedule.lesson_id.in_(other_lessons),
            )
            .execution_options(synchronize_session=False)
        )

    async def get_schedule(
        self,
        db: AsyncSession,
        user_id: str,
        upcoming_only: bool = False,
        roadmap_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        # Joining through Roadmap.user_id hides any session whose lesson is not in the caller's roadmap.
        stmt = (
            select(StudySchedule, Lesson.title, Lesson.lesson_content)
            .join(Lesson, StudySchedule.lesson_id == Lesson.id)
            .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
            .where(StudySchedule.user_id == user_id, Roadmap.user_id == user_id)
            .order_by(StudySchedule.scheduled_date.asc(), StudySchedule.id.asc())
        )
        if roadmap_id is not None:
            stmt = stmt.where(Roadmap.id == roadmap_id)
        if upcoming_only:
            stmt = stmt.where(StudySchedule.status.in_(OPEN_SESSION_STATUSES))

        res = await db.execute(stmt)
        return [_session_dict(s, title, content) for s, title, content in res.all()]

    async def update_status(
        self,
        db: AsyncSession,
        schedule_id: str,
        new_status: str,
        user_id: str
    ) -> Dict[str, Any]:
        if new_status not in SESSION_STATUSES:
            raise StepError("Invalid session status", status_code=422)

        res = await db.execute(
            select(StudySchedule, Lesson.title, Lesson.lesson_content)
            .join(Lesson, StudySchedule.lesson_id == Lesson.id)
            .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
            .where(
                StudySchedule.id == schedule_id,
                StudySchedule.user_id == user_id,
                Roadmap.user_id == user_id,
            )
        )
        row = res.one_or_none()
        if row is None:
            raise NotFoundError("Study session not found")

        session, title, content = row
        session.status = new_status
        lesson_row = (await db.execute(select(Lesson).where(Lesson.id == session.lesson_id))).scalar_one()
        from app.services.lesson_status import set_lesson_status
        lesson_target = {"completed": "completed", "skipped": "skipped", "pending": "pending"}[new_status]
        if lesson_row.status != "in_progress" or lesson_target != "pending":
            await set_lesson_status(db, user_id, lesson_row, lesson_target)
        session.status = new_status
        payload = _session_dict(session, title, content)
        await db.commit()
        return payload

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_owned_active_roadmap(db: AsyncSession, user_id: str, roadmap_id: str) -> Roadmap:
        res = await db.execute(
            select(Roadmap).where(
                Roadmap.id == roadmap_id,
                Roadmap.user_id == user_id,
                Roadmap.is_active.is_(True),
            )
        )
        roadmap = res.scalar_one_or_none()
        if roadmap is None:
            # Foreign, unknown and inactive roadmaps get the same answer, so ids cannot be probed.
            raise NotFoundError("Active roadmap not found")
        return roadmap

    @staticmethod
    async def _profile(db: AsyncSession, user_id: str) -> Optional[LearnerProfile]:
        res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
        return res.scalar_one_or_none()

    @staticmethod
    async def _pending_lessons(db: AsyncSession, roadmap_id: str) -> List[Lesson]:
        res = await db.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.roadmap_id == roadmap_id,
                Module.is_planned_later.is_not(True),
                or_(Lesson.status.is_(None), Lesson.status.not_in(FINISHED_LESSON_STATUSES)),
            )
            .order_by(Module.order_index, Lesson.order_index, Lesson.id)
        )
        return list(res.scalars().all())

    @staticmethod
    async def _lesson_by_title(db: AsyncSession, roadmap_id: str, title: str) -> Optional[Lesson]:
        # Exact match. weak_areas hold the lesson title verbatim, so no LIKE pattern is involved.
        res = await db.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.roadmap_id == roadmap_id,
                Module.is_planned_later.is_not(True),
                Lesson.title == title,
            )
            .order_by(Module.order_index, Lesson.order_index, Lesson.id)
            .limit(1)
        )
        return res.scalars().first()


scheduler_service = StudySchedulerService()
