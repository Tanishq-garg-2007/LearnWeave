import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import CycleRun, Lesson, Assessment, User
from app.services.lesson_agent import lesson_agent
from app.services.doubt_agent import doubt_agent
from app.services.quiz_agent import quiz_agent
from app.services.evaluation_agent import evaluation_agent
from app.services.adaptive_agent import adaptive_agent
from app.schemas.lessons import QuizSubmitRequest

logger = logging.getLogger("learnweave.cycle_engine")

VALID_STEPS = ["pending", "lesson_gen", "doubt", "quiz_gen", "eval", "adaptive", "completed"]


class LearningCycleEngine:
    """
    Drives the 6-step agentic learning cycle with persistent multi-session state:
    pending -> lesson_gen -> doubt -> quiz_gen -> eval -> adaptive -> completed
    Ensures idempotency, step caching, and seamless resumption across disconnects.
    """

    async def get_or_create_cycle(
        self,
        db: AsyncSession,
        user: User,
        lesson_id: str,
        idempotency_key: Optional[str] = None
    ) -> CycleRun:
        # Check active existing cycle
        stmt = select(CycleRun).where(
            and_(
                CycleRun.user_id == user.id,
                CycleRun.lesson_id == lesson_id,
                CycleRun.status.in_(["pending", "running", "paused"])
            )
        )
        res = await db.execute(stmt)
        cycle = res.scalars().first()
        if cycle:
            return cycle

        # Create new cycle run
        ikey = idempotency_key or f"cycle_{user.id}_{lesson_id}_{uuid.uuid4().hex[:8]}"
        cycle = CycleRun(
            user_id=user.id,
            lesson_id=lesson_id,
            current_step="lesson_gen",
            status="running",
            step_inputs={},
            step_outputs={},
            idempotency_key=ikey
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)
        return cycle

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
            raise ValueError(f"Cycle run {cycle_id} not found")

        inputs = dict(cycle.step_inputs or {})
        outputs = dict(cycle.step_outputs or {})

        if input_data:
            inputs[step_name] = input_data

        # 1. Idempotent check: if already completed and cached, return immediately
        if step_name in outputs and outputs[step_name]:
            logger.info(f"Reusing cached output for step {step_name} in cycle {cycle_id}")
            return outputs[step_name]

        lesson_id = cycle.lesson_id

        try:
            if step_name == "lesson_gen":
                content = await lesson_agent.generate_lesson(db=db, lesson_id=lesson_id, user=user)
                step_res = content.model_dump()
                outputs["lesson_gen"] = step_res
                cycle.current_step = "doubt"

            elif step_name == "doubt":
                doubt_text = (input_data.get("doubt") if input_data else None) or "Overview of key lesson topics"
                doubt_resp = await doubt_agent.resolve_doubt(
                    db=db,
                    lesson_id=lesson_id,
                    doubt_text=doubt_text,
                    user=user
                )
                step_res = doubt_resp.model_dump()
                outputs["doubt"] = step_res
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
                cycle.current_step = "eval"

            elif step_name == "eval":
                if not input_data or "answers" not in input_data:
                    raise ValueError("Evaluation step requires 'answers' in input data")

                assessment_id = input_data.get("assessment_id")
                if not assessment_id:
                    # Look up from quiz_gen
                    quiz_step = outputs.get("quiz_gen", {})
                    assessment_id = quiz_step.get("assessment_id")
                if not assessment_id:
                    a_res = await db.execute(select(Assessment).where(Assessment.lesson_id == lesson_id))
                    assessment = a_res.scalars().first()
                    assessment_id = assessment.id if assessment else None

                if not assessment_id:
                    raise ValueError("No assessment found to evaluate")

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
                eval_data = outputs.get("eval")
                if not eval_data:
                    raise ValueError("Adaptive step requires completed evaluation outputs")

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

            else:
                raise ValueError(f"Unknown step {step_name}")

            cycle.step_inputs = inputs
            cycle.step_outputs = outputs
            await db.commit()
            await db.refresh(cycle)

            return step_res

        except Exception as exc:
            logger.error(f"Cycle execution error at step {step_name}: {exc}", exc_info=True)
            cycle.error_message = str(exc)
            cycle.status = "failed"
            await db.commit()
            raise

    async def get_cycle_status(self, db: AsyncSession, cycle_id: str, user_id: str) -> Dict[str, Any]:
        res = await db.execute(
            select(CycleRun).where(CycleRun.id == cycle_id, CycleRun.user_id == user_id)
        )
        cycle = res.scalar_one_or_none()
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

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
