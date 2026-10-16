import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Lesson, Assessment, User
from app.services.groq_client import groq_client
from app.schemas.lessons import QuizResponse, QuizQuestionItem

logger = logging.getLogger("learnweave.quiz_agent")

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


class QuizAgent:
    """
    Generates formative assessments consisting of:
    - 3 Multiple Choice Questions (MCQs) for concept recognition and discrimination.
    - 1 Short Answer conceptual question for deep comprehension.
    """

    async def generate_quiz(
        self,
        db: AsyncSession,
        lesson_id: str,
        user: User
    ) -> Assessment:
        # Check if assessment already exists for this lesson
        res = await db.execute(select(Assessment).where(Assessment.lesson_id == lesson_id))
        existing = res.scalars().first()
        if existing:
            return existing

        # Load lesson
        l_res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = l_res.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")

        content_context = ""
        if lesson.lesson_content:
            summary = lesson.lesson_content.get("summary", "")
            sections = " ".join([s.get("content", "") for s in lesson.lesson_content.get("sections", [])])
            takeaways = "\n".join(lesson.lesson_content.get("key_takeaways", []))
            content_context = f"Summary: {summary}\nKey Material: {sections[:1200]}\nTakeaways:\n{takeaways}"
        else:
            content_context = f"Topic: {lesson.title}. Focus on core foundational principles."

        prompt = f"""Generate a rigorous, formative assessment for the lesson:
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

        system_msg = "You are a senior pedagogy and assessment design specialist. Output strictly valid JSON."

        try:
            raw_data = await groq_client.generate_structured_json(
                prompt=prompt,
                schema=QUIZ_SCHEMA,
                system_message=system_msg,
                temperature=0.2,
                max_tokens=850
            )
            questions = self._sanitize_questions(raw_data.get("questions", []), lesson.title)
        except Exception as exc:
            logger.warning(f"Quiz generation via Groq failed: {exc}. Generating deterministic fallback quiz.")
            questions = self._generate_fallback_questions(lesson.title)

        assessment = Assessment(
            lesson_id=lesson.id,
            title=f"Quiz: {lesson.title}",
            assessment_type="quiz",
            questions=questions
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        return assessment

    def _sanitize_questions(self, raw_questions: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
        sanitized = []
        for idx, q in enumerate(raw_questions[:4]):
            q_type = q.get("question_type", "mcq")
            if idx < 3:
                # Force first 3 to be mcq
                q_type = "mcq"
                opts = q.get("options") or {
                    "A": "Primary operational principle",
                    "B": "Secondary redundant mechanism",
                    "C": "Degraded state recovery",
                    "D": "Unbounded concurrent execution"
                }
                correct = q.get("correct_answer", "A").strip().upper()
                if correct not in ["A", "B", "C", "D"]:
                    correct = "A"
                sanitized.append({
                    "question_index": idx,
                    "question_type": "mcq",
                    "question": q.get("question", f"Which is a central principle of {topic}?"),
                    "options": opts,
                    "correct_answer": correct,
                    "explanation": q.get("explanation", "Standard foundational property.")
                })
            else:
                # 4th is short answer
                sanitized.append({
                    "question_index": idx,
                    "question_type": "short_answer",
                    "question": q.get("question", f"Explain in your own words the architectural role of {topic}."),
                    "ideal_answer": q.get("ideal_answer", f"{topic} ensures resource boundaries and coordinated state execution."),
                    "rubric_criteria": q.get("rubric_criteria", ["Mentions core purpose", "Addresses trade-offs"])
                })

        # Ensure exactly 4
        while len(sanitized) < 4:
            sanitized = self._generate_fallback_questions(topic)
            break
        return sanitized

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
