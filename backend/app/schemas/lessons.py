from typing import List, Optional, Dict, Any
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


class LessonGenerateResponse(BaseModel):
    lesson_id: str
    title: str
    status: str
    grounding_type: str
    content: LessonContent


class DoubtRequest(BaseModel):
    doubt: str


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
    question_index: int
    selected_option: Optional[str] = None
    written_answer: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    answers: List[StudentAnswer]


class AnswerEvaluation(BaseModel):
    question_index: int
    question_type: str
    student_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: bool
    score: float
    feedback: str


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
