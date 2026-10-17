from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import User, Roadmap, RoadmapVersion, Module, Lesson
from app.schemas.roadmaps import RoadmapDetailResponse, RescheduleLessonRequest
from app.api.deps import get_current_user
from app.services.lesson_status import set_lesson_status
from app.services.errors import StepError

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


@router.get("/active", response_model=RoadmapDetailResponse)
async def get_active_roadmap(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the student's currently active learning roadmap."""
    query = (
        select(Roadmap)
        .options(selectinload(Roadmap.modules).selectinload(Module.lessons))
        .where(Roadmap.user_id == user.id, Roadmap.is_active == True)
        .order_by(Roadmap.updated_at.desc())
    )
    res = await db.execute(query)
    roadmap = res.scalars().first()
    if not roadmap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active roadmap found for current student")
    return roadmap


@router.get("/{roadmap_id}", response_model=RoadmapDetailResponse)
async def get_roadmap(
    roadmap_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve complete roadmap structure with all modules and lessons."""
    query = (
        select(Roadmap)
        .options(selectinload(Roadmap.modules).selectinload(Module.lessons))
        .where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id)
    )
    res = await db.execute(query)
    roadmap = res.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found or access denied")
    return roadmap


@router.get("/{roadmap_id}/versions")
async def get_roadmap_versions(
    roadmap_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve version history of changes and adaptations made to this roadmap."""
    # Verify ownership
    r_check = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id))
    if not r_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

    res = await db.execute(
        select(RoadmapVersion)
        .where(RoadmapVersion.roadmap_id == roadmap_id)
        .order_by(RoadmapVersion.version_number.desc())
    )
    versions = res.scalars().all()
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "change_reason": v.change_reason,
            "created_at": v.created_at
        }
        for v in versions
    ]


@router.put("/lessons/{lesson_id}/status")
async def update_lesson_status(
    lesson_id: str,
    req: RescheduleLessonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update progress status of an individual lesson."""
    res = await db.execute(
        select(Lesson)
        .join(Roadmap, Lesson.roadmap_id == Roadmap.id)
        .where(Lesson.id == lesson_id, Roadmap.user_id == user.id)
    )
    lesson = res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found or access denied")

    if req.new_status:
        try:
            await set_lesson_status(db, user.id, lesson, req.new_status)
        except StepError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await db.commit()
    return {"status": "success", "lesson_id": lesson.id, "current_status": lesson.status}
