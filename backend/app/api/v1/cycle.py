import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.api.error_utils import internal_error
from app.services.cycle_engine import cycle_engine
from app.services.errors import NotFoundError, StepError
from app.services.quiz_agent import QuizGenerationError

logger = logging.getLogger("learnweave.api.cycle")
from app.api.rate_limit import limit_by_ip, limit_by_user

RETRY_AFTER = "30"


def _unavailable(exc: BaseException, public_message: str) -> HTTPException:
    err = internal_error(logger, exc, public_message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    err.headers = {"Retry-After": RETRY_AFTER}
    return err


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



@router.post("/start", dependencies=[Depends(limit_by_user('cycle_start', 10, 60))])
async def start_or_resume_cycle(
    req: CycleStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start or resume the agentic learning cycle for a lesson.
    If a cycle is already in progress, returns the existing cycle.
    """
    try:
        cycle = await cycle_engine.get_or_create_cycle(
            db=db,
            user=user,
            lesson_id=req.lesson_id,
            idempotency_key=req.idempotency_key
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StepError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Could not start the learning cycle")
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
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{cycle_id}/step", dependencies=[Depends(limit_by_user('cycle_step', 20, 60, llm=True))])
async def execute_cycle_step(
    cycle_id: str,
    req: StepExecuteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a designated cycle step (lesson_gen, doubt, quiz_gen, eval, adaptive).
    Idempotent: reuses cached step outputs if already executed. Steps must run in order.
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
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except QuizGenerationError as exc:
        raise _unavailable(exc, "Quiz generation is temporarily unavailable")
    except StepError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        raise internal_error(logger, exc, "Cycle step failed; you can retry it")
