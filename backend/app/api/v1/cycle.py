import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.cycle_engine import cycle_engine

logger = logging.getLogger("learnweave.api.cycle")
router = APIRouter(prefix="/cycle", tags=["Learning Cycle State Machine"])


class CycleStartRequest(BaseModel):
    lesson_id: str
    idempotency_key: Optional[str] = None


class StepExecuteRequest(BaseModel):
    step_name: str
    input_data: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

    def get_input(self) -> Dict[str, Any]:
        return self.input_data or self.payload or {}



@router.post("/start")
async def start_or_resume_cycle(
    req: CycleStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start or resume the 6-step agentic learning cycle for a lesson.
    If a cycle is already in progress, returns the existing cycle.
    """
    cycle = await cycle_engine.get_or_create_cycle(
        db=db,
        user=user,
        lesson_id=req.lesson_id,
        idempotency_key=req.idempotency_key
    )
    return {
        "cycle_id": cycle.id,
        "lesson_id": cycle.lesson_id,
        "current_step": cycle.current_step,
        "status": cycle.status,
        "completed_steps": list((cycle.step_outputs or {}).keys()),
        "step_outputs": cycle.step_outputs or {}
    }


@router.get("/{cycle_id}")
async def get_cycle_status(
    cycle_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full cycle execution status and cached step outputs."""
    try:
        status_data = await cycle_engine.get_cycle_status(db=db, cycle_id=cycle_id, user_id=user.id)
        return status_data
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{cycle_id}/step")
async def execute_cycle_step(
    cycle_id: str,
    req: StepExecuteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a designated cycle step (e.g. lesson_gen, doubt, quiz_gen, eval, adaptive).
    Idempotent: Reuses cached step outputs if already executed.
    """
    try:
        step_result = await cycle_engine.execute_step(
            db=db,
            cycle_id=cycle_id,
            step_name=req.step_name,
            user=user,
            input_data=req.get_input()
        )
        status_data = await cycle_engine.get_cycle_status(db=db, cycle_id=cycle_id, user_id=user.id)
        return {
            "step_name": req.step_name,
            "step_result": step_result,
            "cycle": status_data
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Cycle step execution failed: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
