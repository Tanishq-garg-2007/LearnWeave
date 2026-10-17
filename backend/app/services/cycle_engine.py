import hashlib
import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import CycleRun, User
from app.services.errors import NotFoundError, StepError
from app.services.ownership import get_owned_lesson
from app.services.lesson_agent import lesson_agent
from app.services.doubt_agent import doubt_agent
from app.services.quiz_agent import quiz_agent
from app.services.evaluation_agent import evaluation_agent
from app.services.adaptive_agent import adaptive_agent
from app.schemas.lessons import QuizSubmitRequest

logger = logging.getLogger("learnweave.cycle_engine")

VALID_STEPS = ["lesson_gen", "doubt", "quiz_gen", "eval", "adaptive"]
ACTIVE_STATUSES = ["pending", "running", "paused"]

# A step may run only after these steps have completed in the same cycle.
STEP_PREREQUISITES: Dict[str, List[str]] = {
    "lesson_gen": [],
    "doubt": ["lesson_gen"],
    "quiz_gen": ["lesson_gen"],
    "eval": ["quiz_gen"],
    "adaptive": ["eval"],
}
DEFAULT_DOUBT = "Overview of key lesson topics"


def _doubt_cache_key(doubt_text: str) -> str:
    """Doubt answers are cached per question text, so a different question is never answered from cache."""
    digest = hashlib.sha256(doubt_text.encode("utf-8")).hexdigest()[:16]
    return f"doubt:{digest}"


class LearningCycleEngine:
    """
    Drives the 5-step agentic learning cycle with persistent multi-session state:
    lesson_gen -> doubt* -> quiz_gen -> eval -> adaptive (doubt may be asked any time before eval).
    Ensures idempotency, step caching, and seamless resumption across disconnects.
    """

    async def get_or_create_cycle(
        self,
        db: AsyncSession,
        user: User,
        lesson_id: str,
        idempotency_key: Optional[str] = None
    ) -> CycleRun:
        # The lesson must exist and belong to this user before anything is created.
        await get_owned_lesson(db, lesson_id, user)

        # Replays of the same idempotency key return the same cycle, whatever its status.
        if idempotency_key:
            key_cycle = await self._find_by_idempotency_key(db, user, idempotency_key)
            if key_cycle is not None:
                if key_cycle.lesson_id != lesson_id:
                    raise StepError("idempotency_key was already used for a different lesson", status_code=409)
                return key_cycle

        active = await self._find_active(db, user, lesson_id)
        if active is not None:
            return active

        ikey = idempotency_key or f"cycle_{user.id}_{lesson_id}_{uuid.uuid4().hex[:8]}"
        cycle_id = str(uuid.uuid4())

        # INSERT ... ON CONFLICT DO NOTHING covers both races: the partial unique index
        # (one active cycle per user and lesson) and the per-user idempotency key.
        # A losing request simply reads the winner's row, with no exception and no rollback.
        insert_stmt = (
            pg_insert(CycleRun)
            .values(
                id=cycle_id,
                user_id=user.id,
                lesson_id=lesson_id,
                current_step="lesson_gen",
                status="running",
                step_inputs={},
                step_outputs={},
                idempotency_key=ikey,
            )
            .on_conflict_do_nothing()
        )
        result = await db.execute(insert_stmt)
        await db.commit()

        if result.rowcount == 1:
            cycle = await db.get(CycleRun, cycle_id)
            await db.refresh(cycle)
            return cycle

        winner = None
        if idempotency_key:
            winner = await self._find_by_idempotency_key(db, user, idempotency_key)
        if winner is None:
            winner = await self._find_active(db, user, lesson_id)
        if winner is None:
            raise StepError("Could not start the cycle, please retry", status_code=409)
        return winner

    async def _find_active(self, db: AsyncSession, user: User, lesson_id: str) -> Optional[CycleRun]:
        res = await db.execute(
            select(CycleRun).where(
                and_(
                    CycleRun.user_id == user.id,
                    CycleRun.lesson_id == lesson_id,
                    CycleRun.status.in_(ACTIVE_STATUSES)
                )
            )
        )
        return res.scalars().first()

    async def _find_by_idempotency_key(self, db: AsyncSession, user: User, key: str) -> Optional[CycleRun]:
        res = await db.execute(
            select(CycleRun).where(CycleRun.user_id == user.id, CycleRun.idempotency_key == key)
        )
        return res.scalars().first()

    async def execute_step(
        self,
        db: AsyncSession,
        cycle_id: str,
        step_name: str,
        user: User,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        res = await db.execute(
            select(CycleRun).where(CycleRun.id == cycle_id, CycleRun.user_id == user.id)
        )
        cycle = res.scalar_one_or_none()
        if not cycle:
            raise NotFoundError(f"Cycle run {cycle_id} not found")

        if step_name not in VALID_STEPS:
            raise StepError(f"Unknown step '{step_name}'. Valid steps: {', '.join(VALID_STEPS)}")

        inputs = dict(cycle.step_inputs or {})
        outputs = dict(cycle.step_outputs or {})
        lesson_id = cycle.lesson_id

        # Cached outputs are returned first, so re-running a finished step is always safe.
        cache_key = step_name
        if step_name == "doubt":
            doubt_text = self._doubt_text(input_data)
            cache_key = _doubt_cache_key(doubt_text)
        if outputs.get(cache_key):
            logger.info(f"Reusing cached output for step {cache_key} in cycle {cycle_id}")
            return outputs[cache_key]

        self._check_prerequisites(step_name, outputs)

        if input_data:
            inputs[step_name] = input_data

        try:
            if step_name == "lesson_gen":
                _, content, _ = await lesson_agent.ensure_lesson_content(db=db, lesson_id=lesson_id, user=user)
                step_res = content.model_dump()
                outputs["lesson_gen"] = step_res
                if cycle.current_step == "lesson_gen":
                    cycle.current_step = "doubt"

            elif step_name == "doubt":
                doubt_resp = await doubt_agent.resolve_doubt(
                    db=db,
                    lesson_id=lesson_id,
                    doubt_text=doubt_text,
                    user=user
                )
                step_res = doubt_resp.model_dump()
                outputs[cache_key] = step_res
                outputs["doubt"] = step_res  # latest doubt, kept for status display
                if cycle.current_step == "doubt":
                    cycle.current_step = "quiz_gen"

            elif step_name == "quiz_gen":
                assessment = await quiz_agent.generate_quiz(db=db, lesson_id=lesson_id, user=user)
                sanitized_questions = []
                for q in (assessment.questions or []):
                    sanitized_questions.append({
                        "question_index": q["question_index"],
                        "question_type": q["question_type"],
                        "question": q["question"],
                        "options": q.get("options"),
                        "rubric_criteria": q.get("rubric_criteria")
                    })
                step_res = {
                    "assessment_id": assessment.id,
                    "lesson_id": assessment.lesson_id,
                    "title": assessment.title,
                    "questions": sanitized_questions
                }
                outputs["quiz_gen"] = step_res
                if cycle.current_step in ("lesson_gen", "doubt", "quiz_gen"):
                    cycle.current_step = "eval"

            elif step_name == "eval":
                if not input_data or "answers" not in input_data:
                    raise StepError("Evaluation step requires 'answers' in input data")

                # Grade against the assessment this cycle generated, never a client-supplied id.
                assessment_id = outputs["quiz_gen"]["assessment_id"]

                sub_req = QuizSubmitRequest.model_validate(input_data)
                eval_resp = await evaluation_agent.evaluate_submission(
                    db=db,
                    assessment_id=assessment_id,
                    submission=sub_req,
                    user=user
                )
                step_res = eval_resp.model_dump()
                outputs["eval"] = step_res
                cycle.current_step = "adaptive"

            elif step_name == "adaptive":
                eval_data = outputs["eval"]

                overall_score = float(eval_data.get("overall_score", 0.0))
                passed = bool(eval_data.get("passed", False))

                adapt_res = await adaptive_agent.adapt_after_assessment(
                    db=db,
                    lesson_id=lesson_id,
                    overall_score=overall_score,
                    passed=passed,
                    user=user
                )
                step_res = adapt_res
                outputs["adaptive"] = step_res
                cycle.current_step = "completed"
                cycle.status = "completed"

            cycle.step_inputs = inputs
            cycle.step_outputs = outputs
            cycle.error_message = None
            await db.commit()
            await db.refresh(cycle)

            return step_res

        except StepError:
            # Client-side mistake: the cycle is untouched and the step can be retried with valid input.
            await db.rollback()
            raise
        except Exception as exc:
            logger.error(f"Cycle execution error at step {step_name} (cycle {cycle_id}): {exc!r}", exc_info=True)
            # Roll back the failed work, then record the failure without ending the cycle,
            # so the client can resume and retry this step.
            await db.rollback()
            fresh = (await db.execute(select(CycleRun).where(CycleRun.id == cycle_id))).scalar_one_or_none()
            if fresh is not None:
                fresh.error_message = f"Step '{step_name}' failed. It can be retried."
                await db.commit()
            raise

    @staticmethod
    def _doubt_text(input_data: Optional[Dict[str, Any]]) -> str:
        raw = (input_data or {}).get("doubt") if input_data else None
        text = raw.strip() if isinstance(raw, str) and raw.strip() else DEFAULT_DOUBT
        return text

    @staticmethod
    def _check_prerequisites(step_name: str, outputs: Dict[str, Any]) -> None:
        missing = [s for s in STEP_PREREQUISITES[step_name] if not outputs.get(s)]
        if missing:
            raise StepError(
                f"Step '{step_name}' requires these steps to complete first: {', '.join(missing)}",
                status_code=409,
            )
        if step_name == "doubt" and outputs.get("eval"):
            raise StepError("Doubts cannot be asked after the assessment has been evaluated", status_code=409)

    async def get_cycle_status(self, db: AsyncSession, cycle_id: str, user_id: str) -> Dict[str, Any]:
        res = await db.execute(
            select(CycleRun).where(CycleRun.id == cycle_id, CycleRun.user_id == user_id)
        )
        cycle = res.scalar_one_or_none()
        if not cycle:
            raise NotFoundError(f"Cycle {cycle_id} not found")

        return {
            "id": cycle.id,
            "lesson_id": cycle.lesson_id,
            "current_step": cycle.current_step,
            "status": cycle.status,
            "completed_steps": list((cycle.step_outputs or {}).keys()),
            "step_outputs": cycle.step_outputs or {},
            "error_message": cycle.error_message,
            "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
            "updated_at": cycle.updated_at.isoformat() if cycle.updated_at else None
        }


cycle_engine = LearningCycleEngine()
