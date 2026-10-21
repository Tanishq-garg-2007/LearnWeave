import logging
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BeforeValidator, Field, StringConstraints, TypeAdapter, field_validator, BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, AssessmentAttempt, User
from app.services.errors import NotFoundError, StepError
from app.services.ownership import get_owned_lesson
from app.services.groq_client import groq_client
from app.schemas.lessons import QuizQuestionItem, QuizResponse

logger = logging.getLogger("learnweave.quiz_agent")

QUIZ_QUESTION_COUNT = 4
MCQ_COUNT = 3  # questions 0..2 are MCQs, question 3 is short answer
OPTION_KEYS = ("A", "B", "C", "D")

QUIZ_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_index": {"type": "integer"},
                    "question_type": {"type": "string", "enum": ["mcq", "short_answer"]},
                    "question": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"}
                        },
                        "required": ["A", "B", "C", "D"]
                    },
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                    "ideal_answer": {"type": "string"},
                    "rubric_criteria": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["question_index", "question_type", "question"]
            }
        }
    },
    "required": ["title", "questions"]
}


# ---------------------------------------------------------------------------
# Strict question schema. Model output is validated, never repaired with defaults:
# a missing option, a null answer key or a malformed rubric rejects the whole quiz.
# ---------------------------------------------------------------------------

def _strip_upper(value: Any) -> Any:
    return value.strip().upper() if isinstance(value, str) else value


def _normalise_option_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k).strip().upper(): v for k, v in value.items()}
    return value


StemText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
CorrectLetter = Annotated[Literal["A", "B", "C", "D"], BeforeValidator(_strip_upper)]


class McqQuestion(BaseModel):
    question_index: int
    question_type: Literal["mcq"]
    question: StemText
    options: Annotated[Dict[Literal["A", "B", "C", "D"], ShortText], BeforeValidator(_normalise_option_keys)]
    correct_answer: CorrectLetter
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, max_length=600)] = ""

    @field_validator("options")
    @classmethod
    def _exactly_four_options(cls, value: Dict[str, str]) -> Dict[str, str]:
        if set(value) != set(OPTION_KEYS):
            raise ValueError("options must contain exactly A, B, C and D")
        return value


class ShortAnswerQuestion(BaseModel):
    question_index: int
    question_type: Literal["short_answer"]
    question: StemText
    ideal_answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1500)]
    rubric_criteria: Annotated[List[ShortText], Field(min_length=1, max_length=5)]


QuizQuestion = Annotated[Union[McqQuestion, ShortAnswerQuestion], Field(discriminator="question_type")]
_QUESTION_ADAPTER: TypeAdapter = TypeAdapter(QuizQuestion)


def validate_quiz_questions(raw: Any) -> List[Dict[str, Any]]:
    """Return the normalised stored form of a quiz, or raise ValueError.

    Question indexes are taken from position, and question types must follow the fixed layout
    (three MCQs, then one short answer).
    """
    if not isinstance(raw, list) or len(raw) != QUIZ_QUESTION_COUNT:
        raise ValueError(f"a quiz needs exactly {QUIZ_QUESTION_COUNT} questions")
    normalised: List[Dict[str, Any]] = []
    for position, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"question {position} is not an object")
        question = _QUESTION_ADAPTER.validate_python({**item, "question_index": position})
        expected = "mcq" if position < MCQ_COUNT else "short_answer"
        if question.question_type != expected:
            raise ValueError(f"question {position} must be {expected}")
        normalised.append(question.model_dump())
    return normalised


def build_quiz_response(assessment: Assessment) -> QuizResponse:
    """Student-facing view of a quiz. Answer keys and ideal answers are never included."""
    try:
        questions = validate_quiz_questions(assessment.questions)
    except ValueError as exc:
        logger.error(f"Stored quiz {assessment.id} failed validation: {exc}")
        raise StepError("This quiz is damaged and must be regenerated.", status_code=409)
    items = [
        QuizQuestionItem(
            question_index=q["question_index"],
            question_type=q["question_type"],
            question=q["question"],
            options=q.get("options"),
            rubric_criteria=q.get("rubric_criteria"),
        )
        for q in questions
    ]
    return QuizResponse(
        assessment_id=assessment.id,
        lesson_id=assessment.lesson_id,
        title=assessment.title,
        questions=items,
    )


class QuizGenerationError(Exception):
    """The model returned output that is not a valid quiz. Nothing has been stored."""


class QuizAgent:
    """
    Generates formative assessments consisting of:
    - 3 Multiple Choice Questions (MCQs) for concept recognition and discrimination.
    - 1 Short Answer conceptual question for deep comprehension.

    Generation (POST /lessons/{id}/quiz) is idempotent: one quiz per lesson, enforced by a unique
    constraint. Reads (GET /lessons/{id}/quiz) never call the LLM.
    """

    async def get_current_assessment(self, db: AsyncSession, lesson_id: str, user: User) -> Assessment:
        """Read-only lookup. NotFoundError if the lesson is not the user's or no quiz exists yet."""
        lesson = await get_owned_lesson(db, lesson_id, user)
        assessment = await self._find_assessment(db, lesson.id)
        if assessment is None:
            raise NotFoundError("Quiz has not been generated yet")
        return assessment

    async def generate_quiz(self, db: AsyncSession, lesson_id: str, user: User) -> Assessment:
        lesson = await get_owned_lesson(db, lesson_id, user)

        existing = await self._find_assessment(db, lesson.id)
        if existing is not None:
            try:
                validate_quiz_questions(existing.questions)
                return existing
            except ValueError as exc:
                logger.warning(f"Quiz {existing.id} is invalid ({exc}); regenerating in place.")
                attempts = await db.scalar(
                    select(func.count(AssessmentAttempt.id)).where(AssessmentAttempt.assessment_id == existing.id)
                )
                if attempts:
                    # Attempts were graded against this quiz, so its questions must not change under them.
                    raise StepError("This quiz is damaged and already has attempts. Contact support.", status_code=409)

        questions = await self._generate_questions(lesson)

        if existing is not None:
            existing.questions = questions
            existing.title = f"Quiz: {lesson.title}"
            await db.commit()
            await db.refresh(existing)
            return existing

        # ON CONFLICT: two concurrent requests for the same lesson both succeed, and exactly one row is stored.
        stmt = (
            pg_insert(Assessment)
            .values(
                lesson_id=lesson.id,
                title=f"Quiz: {lesson.title}",
                assessment_type="quiz",
                questions=questions,
            )
            .on_conflict_do_nothing(index_elements=["lesson_id"])
        )
        await db.execute(stmt)
        await db.commit()

        assessment = await self._find_assessment(db, lesson.id)
        if assessment is None:  # cannot happen after a successful insert or an existing conflict row
            raise QuizGenerationError("quiz row missing after insert")
        return assessment

    async def _find_assessment(self, db: AsyncSession, lesson_id: str) -> Optional[Assessment]:
        res = await db.execute(
            select(Assessment)
            .where(Assessment.lesson_id == lesson_id)
            .order_by(Assessment.created_at.asc(), Assessment.id.asc())
            .limit(1)
        )
        return res.scalars().first()

    async def _generate_questions(self, lesson) -> List[Dict[str, Any]]:
        prompt = self._build_prompt(lesson)
        system_msg = "You are a senior pedagogy and assessment design specialist. Output strictly valid JSON."

        try:
            raw_data = await groq_client.generate_structured_json(
                prompt=prompt,
                schema=QUIZ_SCHEMA,
                system_message=system_msg,
                temperature=0.2,
                max_tokens=2200
            )
        except Exception as exc:
            logger.warning(f"Quiz generation via Groq failed: {exc}. Generating deterministic fallback quiz.")
            return self._generate_fallback_questions(lesson.title)

        raw_questions = raw_data.get("questions") if isinstance(raw_data, dict) else None
        try:
            return validate_quiz_questions(raw_questions)
        except ValueError as exc:
            logger.warning(f"Model quiz output failed validation: {exc}")
            raise QuizGenerationError(str(exc)) from exc

    @staticmethod
    def _build_prompt(lesson) -> str:
        content_context = ""
        if lesson.lesson_content:
            summary = lesson.lesson_content.get("summary", "")
            sections = " ".join([s.get("content", "") for s in lesson.lesson_content.get("sections", [])])
            takeaways = "\n".join(lesson.lesson_content.get("key_takeaways", []))
            content_context = f"Summary: {summary}\nKey Material: {sections[:1200]}\nTakeaways:\n{takeaways}"
        else:
            content_context = f"Topic: {lesson.title}. Focus on core foundational principles."

        return f"""Generate a rigorous, formative assessment for the lesson:
Lesson Title: {lesson.title}
Content Context:
{content_context}

REQUIREMENTS:
1. Provide exactly 4 questions:
   - Question 0: Multiple Choice Question (question_type="mcq"). Options A, B, C, D. State `correct_answer` ("A", "B", "C", or "D") and `explanation`.
   - Question 1: Multiple Choice Question (question_type="mcq"). Options A, B, C, D. State `correct_answer` and `explanation`.
   - Question 2: Multiple Choice Question (question_type="mcq"). Options A, B, C, D. State `correct_answer` and `explanation`.
   - Question 3: Conceptual Short-Answer Question (question_type="short_answer"). Provide `ideal_answer` and a list of 2-3 `rubric_criteria` (key concepts the student must articulate).
2. Avoid trivial recall; test analytical understanding and operational trade-offs.
"""

    def _generate_fallback_questions(self, topic: str) -> List[Dict[str, Any]]:
        return [
            {
                "question_index": 0,
                "question_type": "mcq",
                "question": f"What is the primary objective of {topic}?",
                "options": {
                    "A": "To optimize coordination and manage system state effectively",
                    "B": "To bypass operating system kernel security checks",
                    "C": "To eliminate the need for persistent storage",
                    "D": "To force synchronous single-threaded execution"
                },
                "correct_answer": "A",
                "explanation": "Primary design ensures coordinated scheduling and state management."
            },
            {
                "question_index": 1,
                "question_type": "mcq",
                "question": f"Which trade-off is most commonly encountered when scaling {topic}?",
                "options": {
                    "A": "Increased code compilation time only",
                    "B": "Latency overhead vs consistency guarantees",
                    "C": "Loss of floating-point precision",
                    "D": "Permanent degradation of cryptographic randomness"
                },
                "correct_answer": "B",
                "explanation": "Distributed and concurrent systems balance latency against consistency guarantees."
            },
            {
                "question_index": 2,
                "question_type": "mcq",
                "question": f"How does {topic} maintain isolation between independent components?",
                "options": {
                    "A": "Through shared global mutable pointers",
                    "B": "By disabling interrupt lines across CPU cores",
                    "C": "Through clear memory boundaries and defined communication interfaces",
                    "D": "By restarting the host operating system periodically"
                },
                "correct_answer": "C",
                "explanation": "Memory abstraction and explicit interface contracts provide safe isolation."
            },
            {
                "question_index": 3,
                "question_type": "short_answer",
                "question": f"Describe the core workflow of {topic} and give one real-world operational hazard if misconfigured.",
                "ideal_answer": f"{topic} organizes workflow execution systematically. A misconfiguration leads to resource starvation or state inconsistency.",
                "rubric_criteria": [
                    "Describes primary sequence of operation",
                    "Identifies an authentic failure mode or race condition",
                    "Provides clear reasoning"
                ]
            }
        ]


quiz_agent = QuizAgent()
