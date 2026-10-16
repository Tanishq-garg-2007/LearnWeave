import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger("learnweave.api.schedule")
router = APIRouter(prefix="/schedule", tags=["Study Scheduling & Spaced Repetition"])


class GenerateScheduleRequest(BaseModel):
    roadmap_id: str


class UpdateScheduleStatusRequest(BaseModel):
    status: str  # scheduled, completed, missed, rescheduled


@router.post("/generate")
async def generate_schedule(
    req: GenerateScheduleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate or refresh study schedule for the active roadmap."""
    try:
        created = await scheduler_service.generate_sprint_schedule(
            db=db,
            user=user,
            roadmap_id=req.roadmap_id
        )
        return {
            "message": f"Successfully scheduled {len(created)} study sessions.",
            "total_sessions": len(created)
        }
    except Exception as exc:
        logger.error(f"Failed to generate schedule: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("")
async def get_schedule(
    upcoming_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve personal study calendar sessions."""
    items = await scheduler_service.get_schedule(
        db=db,
        user_id=user.id,
        upcoming_only=upcoming_only
    )
    return {"count": len(items), "sessions": items}


@router.put("/{schedule_id}/status")
async def update_session_status(
    schedule_id: str,
    req: UpdateScheduleStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update study session status (e.g. mark completed)."""
    try:
        res = await scheduler_service.update_status(
            db=db,
            schedule_id=schedule_id,
            new_status=req.status,
            user_id=user.id
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
