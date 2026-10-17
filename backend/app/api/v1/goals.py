from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import User, LearningGoal, Roadmap, RoadmapVersion, Module, Lesson, LessonPrerequisite
from app.schemas.roadmaps import GoalCreateRequest, GoalResponse, RoadmapDetailResponse
from app.api.deps import get_current_user
from app.services.roadmap_agent import roadmap_agent, RoadmapValidationError
from app.services.groq_client import GroqClientError
from app.api.error_utils import internal_error
import logging

logger = logging.getLogger("learnweave.api.goals")
from app.services.scheduler_service import scheduler_service

from app.api.rate_limit import limit_by_ip, limit_by_user

router = APIRouter(prefix="/goals", tags=["Learning Goals & Roadmaps"])


@router.post("", response_model=RoadmapDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit_by_user('goal_create', 5, 60, llm=True))])
async def create_goal_and_roadmap(
    req: GoalCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a learning goal and generate a structured, personalized curriculum.
    Persists roadmap, modules, lessons, and the study schedule for the new active roadmap.
    """
    # 1. Persist Learning Goal
    goal = LearningGoal(
        user_id=user.id,
        subject=req.subject,
        target_level=req.target_level,
        current_level=req.current_level,
        total_duration_weeks=req.total_duration_weeks,
        hours_per_week=req.hours_per_week,
        preferred_style=req.preferred_style,
        specific_objectives=req.specific_objectives
    )
    db.add(goal)
    await db.flush()

    # 2. Invoke Roadmap Planning Agent
    prefs = user.profile.preferences if user.profile else {}
    try:
        plan = await roadmap_agent.generate_roadmap(req, learner_preferences=prefs)
    except GroqClientError:
        await db.rollback()
        raise  # global handler maps to 502/503; previous roadmap untouched
    except RoadmapValidationError as exc:
        await db.rollback()
        raise internal_error(logger, exc, "The AI produced an invalid curriculum. Please try again.", status_code=status.HTTP_502_BAD_GATEWAY)
    if not plan.modules or not any(m.lessons for m in plan.modules):
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The AI produced an empty curriculum. Please try again.")

    # 3. Deactivate previous active roadmaps
    await db.execute(
        update(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active.is_(True)).values(is_active=False)
    )

    # Persist Roadmap Record
    roadmap = Roadmap(
        goal_id=goal.id,
        user_id=user.id,
        title=plan.title,
        version=1,
        is_active=True,
        total_modules=len(plan.modules),
        total_lessons=sum(len(m.lessons) for m in plan.modules)
    )
    db.add(roadmap)
    await db.flush()

    # Version history snapshot
    version_snapshot = RoadmapVersion(
        roadmap_id=roadmap.id,
        version_number=1,
        change_reason="Initial curriculum generation by RoadmapPlanningAgent",
        snapshot_data=plan.model_dump()
    )
    db.add(version_snapshot)

    # 4. Persist Modules and Lessons
    title_to_lesson: dict = {}
    for m_idx, mod_plan in enumerate(plan.modules):
        module = Module(
            roadmap_id=roadmap.id,
            title=mod_plan.title,
            description=mod_plan.description,
            order_index=m_idx + 1,
            is_planned_later=mod_plan.is_planned_later,
            target_week=mod_plan.target_week,
            estimated_hours=mod_plan.estimated_hours
        )
        db.add(module)
        await db.flush()

        for l_idx, les_plan in enumerate(mod_plan.lessons):
            lesson = Lesson(
                module_id=module.id,
                roadmap_id=roadmap.id,
                title=les_plan.title,
                learning_objectives=les_plan.learning_objectives,
                order_index=l_idx + 1,
                status="pending",
                duration_minutes=les_plan.duration_minutes,
                lesson_content={"is_revision": les_plan.is_revision}
            )
            db.add(lesson)
            await db.flush()
            title_to_lesson[les_plan.title] = lesson.id
            for pre_title in les_plan.prerequisite_titles:
                pre_id = title_to_lesson.get(pre_title)
                if pre_id and pre_id != lesson.id:
                    db.add(LessonPrerequisite(lesson_id=lesson.id, prerequisite_lesson_id=pre_id))

    # 5. Study schedule: the scheduler honours daily_minutes and only touches the new roadmap.
    await scheduler_service.drop_pending_sessions_except(db, user_id=user.id, keep_roadmap_id=roadmap.id)
    await scheduler_service.generate_sprint_schedule(db, user, roadmap.id, commit=False)
    await db.commit()

    # Reload complete roadmap with relationships
    query = (
        select(Roadmap)
        .options(
            selectinload(Roadmap.modules).selectinload(Module.lessons)
        )
        .where(Roadmap.id == roadmap.id)
    )
    res = await db.execute(query)
    saved_roadmap = res.scalar_one()

    return saved_roadmap


@router.get("", response_model=List[GoalResponse])
async def list_user_goals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all learning goals created by current student."""
    res = await db.execute(
        select(LearningGoal).where(LearningGoal.user_id == user.id).order_by(LearningGoal.created_at.desc())
    )
    return res.scalars().all()


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal_by_id(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve details of a specific goal."""
    res = await db.execute(
        select(LearningGoal).where(LearningGoal.id == goal_id, LearningGoal.user_id == user.id)
    )
    goal = res.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning goal not found")
    return goal
