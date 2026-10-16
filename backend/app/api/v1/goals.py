from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import (
    User, LearningGoal, Roadmap, RoadmapVersion, Module, Lesson, LessonPrerequisite, StudySchedule
)
from app.schemas.roadmaps import GoalCreateRequest, GoalResponse, RoadmapDetailResponse
from app.api.deps import get_current_user
from app.services.roadmap_agent import roadmap_agent

router = APIRouter(prefix="/goals", tags=["Learning Goals & Roadmaps"])


@router.post("", response_model=RoadmapDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_goal_and_roadmap(
    req: GoalCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a learning goal and generate a structured, personalized curriculum.
    Persists roadmap, modules, detailed 2-week lessons, future placeholders, and study schedule.
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
    plan = await roadmap_agent.generate_roadmap(req, learner_preferences=prefs)

    # 3. Deactivate previous active roadmaps
    await db.execute(
        select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)
    )
    from sqlalchemy import update
    await db.execute(
        update(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True).values(is_active=False)
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
    lesson_title_to_id = {}
    schedule_date_cursor = datetime.utcnow() + timedelta(days=1)

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
            lesson_title_to_id[les_plan.title] = lesson.id

            # Initial study schedule
            schedule = StudySchedule(
                user_id=user.id,
                lesson_id=lesson.id,
                scheduled_date=schedule_date_cursor,
                status="scheduled"
            )
            db.add(schedule)
            schedule_date_cursor += timedelta(days=2)

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
