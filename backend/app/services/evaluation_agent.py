import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Lesson, Assessment, AssessmentAttempt, LearnerProfile, User
from app.services.groq_client import groq_client
from app.schemas.lessons import QuizSubmitRequest, QuizSubmitResponse, AnswerEvaluation

logger = logging.getLogger("learnweave.evaluation_agent")

SHORT_ANSWER_EVAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "feedback": {"type": "string"},
        "criteria_met": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["score", "feedback"]
}


class EvaluationAgent:
    """
    Evaluates formative assessments:
    - 100% deterministic Python scoring for MCQs.
    - Rubric-guided LLM evaluation for short-answer questions.
    - Calculates overall mastery score and updates LearnerProfile state persistently.
    """

    async def evaluate_submission(
        self,
        db: AsyncSession,
        assessment_id: str,
        submission: QuizSubmitRequest,
        user: User
    ) -> QuizSubmitResponse:
        # Load assessment and lesson
        res = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        l_res = await db.execute(select(Lesson).where(Lesson.id == assessment.lesson_id))
        lesson = l_res.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson {assessment.lesson_id} not found")

        questions = assessment.questions or []
        student_answers_map = {a.question_index: a for a in submission.answers}

        evaluations: List[AnswerEvaluation] = []
        mcq_scores: List[float] = []
        short_answer_score = 0.0

        for q in questions:
            idx = q.get("question_index", 0)
            q_type = q.get("question_type", "mcq")
            student_sub = student_answers_map.get(idx)

            if q_type == "mcq":
                correct_letter = q.get("correct_answer", "A").strip().upper()
                selected = (student_sub.selected_option.strip().upper() if student_sub and student_sub.selected_option else None)
                is_correct = (selected == correct_letter)
                score = 1.0 if is_correct else 0.0
                mcq_scores.append(score)

                explanation = q.get("explanation", "")
                feedback_msg = (
                    f"Correct! {explanation}" if is_correct
                    else f"Incorrect. You chose ({selected or 'None'}), but the correct answer is ({correct_letter}). {explanation}"
                )

                evaluations.append(AnswerEvaluation(
                    question_index=idx,
                    question_type="mcq",
                    student_answer=selected,
                    correct_answer=correct_letter,
                    is_correct=is_correct,
                    score=score,
                    feedback=feedback_msg
                ))

            elif q_type == "short_answer":
                written = (student_sub.written_answer.strip() if student_sub and student_sub.written_answer else "")
                sa_eval = await self._evaluate_short_answer(
                    question=q.get("question", ""),
                    ideal_answer=q.get("ideal_answer", ""),
                    rubric_criteria=q.get("rubric_criteria", []),
                    student_text=written
                )
                short_answer_score = sa_eval["score"]
                is_pass = short_answer_score >= 0.7

                evaluations.append(AnswerEvaluation(
                    question_index=idx,
                    question_type="short_answer",
                    student_answer=written or "No answer provided",
                    correct_answer=q.get("ideal_answer"),
                    is_correct=is_pass,
                    score=short_answer_score,
                    feedback=sa_eval["feedback"]
                ))

        # Overall Score: 75% MCQs (25% each for 3 MCQs) + 25% Short Answer
        avg_mcq = (sum(mcq_scores) / len(mcq_scores)) if mcq_scores else 0.0
        overall_score = round(0.75 * avg_mcq + 0.25 * short_answer_score, 2)
        passed = overall_score >= 0.70

        # Update Learner Profile
        topic = lesson.title
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()

        mastery_impact: Dict[str, float] = {}

        if profile:
            tm = dict(profile.topic_mastery or {})
            prior_score = tm.get(topic, 0.0)
            new_mastery = round(0.3 * prior_score + 0.7 * overall_score, 2)
            tm[topic] = new_mastery
            profile.topic_mastery = tm
            mastery_impact[topic] = new_mastery

            # Completed lessons and weak areas
            completed = list(profile.completed_lessons or [])
            weak = list(profile.weak_areas or [])

            if passed:
                if lesson.id not in completed:
                    completed.append(lesson.id)
                profile.completed_lessons = completed
                lesson.status = "completed"
                if topic in weak:
                    weak.remove(topic)
                profile.weak_areas = weak
            else:
                if topic not in weak:
                    weak.append(topic)
                profile.weak_areas = weak

        # Store attempt record
        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            user_id=user.id,
            score=overall_score,
            passed=passed,
            answers=[a.model_dump() for a in submission.answers],
            topic_mastery_impact=mastery_impact,
            feedback=f"Achieved {int(overall_score * 100)}% on {lesson.title}. {'Passed!' if passed else 'Review suggested topics.'}"
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)

        return QuizSubmitResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            lesson_id=lesson.id,
            overall_score=overall_score,
            passed=passed,
            mcq_score=round(avg_mcq, 2),
            short_answer_score=round(short_answer_score, 2),
            feedback=attempt.feedback,
            evaluations=evaluations,
            topic_mastery_impact=mastery_impact
        )

    async def _evaluate_short_answer(
        self,
        question: str,
        ideal_answer: str,
        rubric_criteria: List[str],
        student_text: str
    ) -> Dict[str, Any]:
        """Rubric-guided evaluation of open-ended conceptual responses."""
        if not student_text or len(student_text.strip()) < 8:
            return {
                "score": 0.0,
                "feedback": "No substantive response was provided to evaluate.",
                "criteria_met": []
            }

        rubric_str = "\n".join(f"- {c}" for c in rubric_criteria)
        prompt = f"""Evaluate this student response against the rubric.

QUESTION:
{question}

IDEAL / REFERENCE ANSWER:
{ideal_answer}

RUBRIC CRITERIA:
{rubric_str}

STUDENT RESPONSE:
"{student_text}"

INSTRUCTIONS:
1. Assign a score between 0.0 and 1.0 based on conceptual completeness and accuracy.
   - 0.9-1.0: Thorough, accurate, addresses all rubric criteria clearly.
   - 0.7-0.8: Good grasp, covers core points with minor omissions.
   - 0.4-0.6: Partial understanding, mentions related terms but misses core mechanisms.
   - 0.0-0.3: Largely inaccurate or irrelevant.
2. Provide concise, constructive feedback explaining what was done well and what was missing.
"""

        system_msg = "You are an objective academic grader. Output strictly valid JSON matching schema."

        try:
            raw_eval = await groq_client.generate_structured_json(
                prompt=prompt,
                schema=SHORT_ANSWER_EVAL_SCHEMA,
                system_message=system_msg,
                temperature=0.1,
                max_tokens=600
            )
            raw_score = float(raw_eval.get("score", 0.5))
            score = max(0.0, min(1.0, round(raw_score, 2)))
            return {
                "score": score,
                "feedback": raw_eval.get("feedback", "Concept evaluated successfully."),
                "criteria_met": raw_eval.get("criteria_met", [])
            }
        except Exception as exc:
            logger.warning(f"Groq short-answer evaluation failed: {exc}. Using deterministic keyword heuristic.")
            # Deterministic heuristic fallback
            ideal_words = set(ideal_answer.lower().split())
            student_words = set(student_text.lower().split())
            overlap = len(ideal_words.intersection(student_words))
            ratio = min(1.0, overlap / max(5, len(ideal_words) * 0.4))
            score = round(ratio, 2)
            return {
                "score": score,
                "feedback": f"Evaluated response with {int(score * 100)}% conceptual overlap.",
                "criteria_met": ["Heuristic assessment"]
            }


evaluation_agent = EvaluationAgent()
