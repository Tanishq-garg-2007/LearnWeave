"""Regressions for three critical logic bugs. No database or network needed.

1. Generating a lesson must not wipe the metadata it already carries (remedial source link, is_revision).
2. Quiz pass rule: a skipped short answer must not let the student pass.
   (The unanswered-MCQ fix is in the frontend and is covered by `tsc --noEmit`.)
"""
from types import SimpleNamespace

from app.schemas.lessons import QuizSubmitRequest, StudentAnswer
from app.services import evaluation_agent as evaluation_agent_mod
from app.services import lesson_agent as lesson_agent_mod
from app.services.evaluation_agent import PASS_THRESHOLD, SHORT_ANSWER_MIN_FOR_PASS, evaluation_agent, is_passing
from app.services.lesson_agent import LessonAgent, merge_lesson_content
from app.services.learning_topics import REMEDIAL_KEY, remedial_source_id


GENERATED = {
    "title": "Targeted Revision: Lists",
    "summary": "Recap of lists.",
    "sections": [{"heading": "Recap", "content": "Lists are ordered.", "cited_chunk_ids": []}],
    "key_takeaways": ["Lists keep order."],
}


# ---------------------------------------------------------------------------
# Bug 1: lesson_content merge
# ---------------------------------------------------------------------------

def test_merge_keeps_remedial_link_and_revision_flag():
    existing = {"is_revision": True, REMEDIAL_KEY: "orig-1", "trigger_score": 0.5}
    merged = merge_lesson_content(existing, GENERATED)
    assert merged[REMEDIAL_KEY] == "orig-1"
    assert merged["is_revision"] is True
    assert merged["trigger_score"] == 0.5
    assert merged["sections"] == GENERATED["sections"]


def test_merge_generated_content_wins_on_conflict():
    merged = merge_lesson_content({"title": "old", "sections": []}, GENERATED)
    assert merged["title"] == GENERATED["title"]
    assert merged["sections"] == GENERATED["sections"]


def test_merge_without_existing_content_returns_generated_only():
    assert merge_lesson_content(None, GENERATED) == GENERATED
    assert merge_lesson_content({}, GENERATED) == GENERATED


def test_merge_does_not_mutate_the_existing_dict():
    existing = {REMEDIAL_KEY: "orig-1"}
    merge_lesson_content(existing, GENERATED)
    assert existing == {REMEDIAL_KEY: "orig-1"}


class _FakeDb:
    async def execute(self, *_args, **_kwargs):
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    async def commit(self):
        return None


def _revision_lesson():
    return SimpleNamespace(
        id="rev-1",
        title="Targeted Revision: Lists",
        module=SimpleNamespace(title="Data structures"),
        learning_objectives=[],
        lesson_content={"is_revision": True, REMEDIAL_KEY: "orig-1", "trigger_score": 0.5},
        status="pending",
    )


def _patch_generation(monkeypatch, lesson, llm_calls):
    async def owned(db, lesson_id, user, **kwargs):
        return lesson

    async def no_notes(**kwargs):
        return SimpleNamespace(chunks=[], degraded=False)

    async def fake_llm(**kwargs):
        llm_calls.append(kwargs)
        return GENERATED

    async def set_status(db, user_id, target, new_status):
        target.status = new_status
        return new_status

    monkeypatch.setattr(lesson_agent_mod, "get_owned_lesson", owned)
    monkeypatch.setattr(lesson_agent_mod.retriever, "retrieve_detailed", no_notes)
    monkeypatch.setattr(lesson_agent_mod.groq_client, "generate_structured_json", fake_llm)
    monkeypatch.setattr(lesson_agent_mod, "set_lesson_status", set_status)


async def test_generating_a_remedial_revision_keeps_its_source_link(monkeypatch):
    lesson = _revision_lesson()
    calls = []
    _patch_generation(monkeypatch, lesson, calls)

    await LessonAgent().generate_lesson(db=_FakeDb(), lesson_id=lesson.id, user=SimpleNamespace(id="u1"))

    assert len(calls) == 1
    assert lesson.lesson_content["sections"] == GENERATED["sections"]  # generated content was stored
    assert remedial_source_id(lesson) == "orig-1"                      # ...and the link to the source survived
    assert lesson.lesson_content["is_revision"] is True


async def test_cached_remedial_content_is_served_without_regenerating(monkeypatch):
    lesson = _revision_lesson()
    calls = []
    _patch_generation(monkeypatch, lesson, calls)
    agent = LessonAgent()

    await agent.generate_lesson(db=_FakeDb(), lesson_id=lesson.id, user=SimpleNamespace(id="u1"))
    _, content, cached = await agent.ensure_lesson_content(db=_FakeDb(), lesson_id=lesson.id, user=SimpleNamespace(id="u1"))

    assert cached is True
    assert content.title == GENERATED["title"]
    assert len(calls) == 1  # the second call did not hit the LLM
    assert remedial_source_id(lesson) == "orig-1"


# ---------------------------------------------------------------------------
# Bug 3: a skipped short answer must not pass the quiz
# ---------------------------------------------------------------------------

def test_three_correct_mcqs_with_blank_short_answer_do_not_pass():
    # 3/3 MCQ gives 0.75 * 1.0 = 0.75, which used to clear the 0.70 threshold on its own.
    assert 0.75 >= PASS_THRESHOLD
    assert is_passing(overall_score=0.75, short_answer_score=0.0) is False


def test_two_correct_mcqs_with_strong_short_answer_pass():
    assert is_passing(overall_score=0.75, short_answer_score=1.0) is True


def test_partial_short_answer_at_the_minimum_passes():
    assert is_passing(overall_score=0.85, short_answer_score=SHORT_ANSWER_MIN_FOR_PASS) is True


def test_short_answer_below_the_minimum_fails_even_with_high_overall():
    assert is_passing(overall_score=0.85, short_answer_score=0.30) is False


def test_overall_below_threshold_fails_even_with_strong_short_answer():
    assert is_passing(overall_score=0.60, short_answer_score=0.90) is False


def test_overall_threshold_is_inclusive():
    assert is_passing(overall_score=PASS_THRESHOLD, short_answer_score=SHORT_ANSWER_MIN_FOR_PASS) is True


# End-to-end through evaluate_submission, so the call site is covered too.

def _quiz_assessment():
    mcq = lambda i, correct: {
        "question_index": i, "question_type": "mcq", "question": f"Question {i}?",
        "options": {"A": "one", "B": "two", "C": "three", "D": "four"},
        "correct_answer": correct, "explanation": "",
    }
    short = {
        "question_index": 3, "question_type": "short_answer", "question": "Explain lists.",
        "ideal_answer": "Lists are ordered, mutable sequences.", "rubric_criteria": ["ordering", "mutability"],
    }
    return SimpleNamespace(id="a1", lesson_id="l1", questions=[mcq(0, "A"), mcq(1, "B"), mcq(2, "C"), short])


class _EvalDb:
    """Just enough session for evaluate_submission: one lesson lookup, no profile, no attempts yet."""

    def __init__(self, lesson):
        self._lesson = lesson
        self._calls = 0

    async def execute(self, *_args, **_kwargs):
        self._calls += 1
        found = self._lesson if self._calls == 1 else None
        return SimpleNamespace(scalar_one_or_none=lambda: found)

    async def scalar(self, *_args, **_kwargs):
        return 0

    def add(self, obj):
        obj.id = "att-1"

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


def _submission(written: str = ""):
    answers = [
        StudentAnswer(question_index=0, selected_option="A"),
        StudentAnswer(question_index=1, selected_option="B"),
        StudentAnswer(question_index=2, selected_option="C"),
    ]
    if written:
        answers.append(StudentAnswer(question_index=3, written_answer=written))
    return QuizSubmitRequest(answers=answers)


async def test_three_correct_mcqs_and_blank_short_answer_fail_the_quiz(monkeypatch):
    assessment = _quiz_assessment()
    lesson = SimpleNamespace(id="l1", title="Lists", lesson_content={})
    monkeypatch.setattr(evaluation_agent_mod, "get_owned_assessment", _async_return(assessment))

    result = await evaluation_agent.evaluate_submission(
        db=_EvalDb(lesson), assessment_id="a1", submission=_submission(), user=SimpleNamespace(id="u1"),
    )

    assert result.mcq_score == 1.0
    assert result.short_answer_score == 0.0
    assert result.overall_score == 0.75
    assert result.passed is False


async def test_strong_short_answer_with_all_mcqs_correct_passes(monkeypatch):
    assessment = _quiz_assessment()
    lesson = SimpleNamespace(id="l1", title="Lists", lesson_content={})
    monkeypatch.setattr(evaluation_agent_mod, "get_owned_assessment", _async_return(assessment))

    async def grader(**kwargs):
        return {"score": 0.5, "feedback": "Partly right."}

    monkeypatch.setattr(evaluation_agent_mod.groq_client, "generate_structured_json", grader)

    result = await evaluation_agent.evaluate_submission(
        db=_EvalDb(lesson), assessment_id="a1",
        submission=_submission(written="Lists are ordered and mutable, unlike tuples."),
        user=SimpleNamespace(id="u1"),
    )

    assert result.short_answer_score == 0.5
    assert result.overall_score == round(0.75 * 1.0 + 0.25 * 0.5, 2)
    assert result.passed is True


def _async_return(value):
    async def _inner(*_args, **_kwargs):
        return value
    return _inner
