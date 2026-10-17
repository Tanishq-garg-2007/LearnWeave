import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.api.error_utils import internal_error
from app.services.errors import NotFoundError, StepError
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger("learnweave.api.schedule")
router = APIRouter(prefix="/schedule", tags=["Study Scheduling & Spaced Repetition"])


class GenerateScheduleRequest(BaseModel):
    roadmap_id: str = Field(..., min_length=1, max_length=36)


class UpdateScheduleStatusRequest(BaseModel):
    # Anything else is rejected by FastAPI with a 422 (list-shaped detail).
    status: Literal["pending", "completed", "skipped"]


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
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to generate schedule")


@router.get("")
async def get_schedule(
    upcoming_only: bool = False,
    roadmap_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve personal study calendar sessions, optionally for one roadmap."""
    items = await scheduler_service.get_schedule(
        db=db,
        user_id=user.id,
        upcoming_only=upcoming_only,
        roadmap_id=roadmap_id,
    )
    return {"count": len(items), "sessions": items}


@router.put("/{schedule_id}/status")
async def update_session_status(
    schedule_id: str,
    req: UpdateScheduleStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a study session's status to pending, completed or skipped. Returns the updated session."""
    try:
        return await scheduler_service.update_status(
            db=db,
            schedule_id=schedule_id,
            new_status=req.status,
            user_id=user.id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StepError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to update session status")
