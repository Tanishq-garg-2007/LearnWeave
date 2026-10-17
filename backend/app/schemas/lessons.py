from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Section(BaseModel):
    heading: str
    content: str
    cited_chunk_ids: List[str] = Field(default_factory=list)


class CitedChunk(BaseModel):
    chunk_id: str
    note_title: str
    page_number: Optional[int] = None
    snippet: str


class LessonContent(BaseModel):
    title: str
    summary: str
    sections: List[Section] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    grounding_type: str = "ai_generated"  # "rag_grounded" or "ai_generated"
    cited_chunks: List[CitedChunk] = Field(default_factory=list)
    retrieval_degraded: bool = False  # True if note search failed; grounding may be incomplete


class LessonGenerateResponse(BaseModel):
    lesson_id: str
    title: str
    status: str
    grounding_type: str
    content: LessonContent


class DoubtRequest(BaseModel):
    doubt: str = Field(..., min_length=1, max_length=2000)


class DoubtCitation(BaseModel):
    chunk_id: str
    note_title: str
    page_number: Optional[int] = None
    snippet: str


class DoubtResponse(BaseModel):
    lesson_id: str
    doubt: str
    answer: str
    citations: List[DoubtCitation] = Field(default_factory=list)
    retrieval_degraded: bool = False


class QuizQuestionItem(BaseModel):
    question_index: int
    question_type: str  # "mcq" or "short_answer"
    question: str
    options: Optional[Dict[str, str]] = None  # {"A": ..., "B": ..., "C": ..., "D": ...}
    rubric_criteria: Optional[List[str]] = None


class QuizResponse(BaseModel):
    assessment_id: str
    lesson_id: str
    title: str
    questions: List[QuizQuestionItem]


class StudentAnswer(BaseModel):
    question_index: int = Field(ge=0, le=9)
    selected_option: Optional[str] = Field(default=None, max_length=1)
    # Hard cap: the grader prompt is built from this text, so it must stay bounded.
    written_answer: Optional[str] = Field(default=None, max_length=2000)


class QuizSubmitRequest(BaseModel):
    answers: List[StudentAnswer] = Field(max_length=10)
    # Optional. When sent it must be the lesson's current quiz, otherwise the route returns 409.
    assessment_id: Optional[str] = Field(default=None, max_length=36)


class AnswerEvaluation(BaseModel):
    question_index: int
    question_type: str
    student_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: bool
    score: float
    feedback: str
    graded_by: str = "deterministic"  # "deterministic" (MCQ, or no answer given) or "llm" (short answer)


class QuizSubmitResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    lesson_id: str
    overall_score: float
    passed: bool
    mcq_score: float
    short_answer_score: float
    feedback: str
    evaluations: List[AnswerEvaluation]
    topic_mastery_impact: Dict[str, float]
    # Set when the attempt failed: the result of adaptive replanning (remedial lesson, version, schedule).
    adaptation: Optional[Dict[str, Any]] = None
